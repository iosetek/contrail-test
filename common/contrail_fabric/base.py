import test_v1
import fixtures
from common import isolated_creds

import vnc_api_test
from vnc_api.vnc_api import *
import random
import socket
import time
from netaddr import *
from tcutils.util import retry, get_random_mac, get_random_name
from tcutils.tcpdump_utils import *
from fabric.api import run
from floating_ip import *
from common.base import GenericTestBase
from common.base import GenericTestBase
from common.vrouter.base import BaseVrouterTest
from common.servicechain.config import ConfigSvcChain
from fabric.context_managers import settings, hide
from tcutils.util import safe_run, safe_sudo
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from router_fixture import LogicalRouterFixture
import copy
import re
from common.neutron.base import BaseNeutronTest
from common.fabric_utils import FabricUtils
from lif_fixture import LogicalInterfaceFixture
from bms_fixture import BMSFixture
from vm_test import VMFixture


class BaseFabricTest(BaseNeutronTest, FabricUtils):

    @classmethod
    def setUpClass(cls):
        super(BaseFabricTest, cls).setUpClass()
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.interfaces = {'physical': [], 'logical': []}
        cls.bms = dict()
    # end setUpClass

    def create_lif(self, pif_fixture, unit=0, vlan_id=None, interface_type=None):
        lif_name = pif_fixture.name + '.' + str(unit)
        lif = self.useFixture(LogicalInterfaceFixture(name=lif_name,
                              pif_fqname=pif_fixture.fq_name,
                              connections=self.connections,
                              vlan_id=vlan_id,
                              interface_type=interface_type))
        self.interfaces['logical'].append(lif)
        return lif

    def _my_ip(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.vm_ip
        elif type(fixture) == BMSFixture:
            return fixture.bms_ip

    def do_ping_mesh(self, fixtures, expectation=True):
        list_of_ips = set()
        for fixture in fixtures:
            list_of_ips.add(self._my_ip(fixture))
        for fixture in fixtures:
            for ip in list_of_ips - set([self._my_ip(fixture)]):
                fixture.clear_arp()
                assert fixture.ping_with_certainty(ip, expectation=expectation)

class BaseEvpnType5Test(BaseFabricTest):

    def update_encap_priority(self, encaps):
        self.addCleanup(self.set_encap_priority, encaps=self.get_encap_priority())
        return self.set_encap_priority(encaps)
    
    def setup_vns(self, vn=None):
        '''Setup VN
           Input vn format:
                vn = {'count':1,
                    'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True,},
                    }

                vn = {'count':1,
                       'vn1':{
                            'address_allocation_mode':'flat-subnet-only',
                            'ip_fabric':True,
                            'ipam_fq_name': 'default-domain:default-project:ipam0'
                          },
                    }
        '''
        vn_count = vn['count'] if vn else 0
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            address_allocation_mode = vn[vn_id].get(
                'address_allocation_mode', 'user-defined-subnet-only')
            if address_allocation_mode == "flat-subnet-only":
                ipam_fq_name = vn[vn_id].get('ipam_fq_name', None)
                vn_fixture = self.create_vn(
                    vn_name=vn_id,
                    address_allocation_mode = address_allocation_mode,
                    forwarding_mode ="l3",
                   ipam_fq_name = ipam_fq_name, option='contrail')

            else:
                vn_subnet = vn[vn_id].get('subnet',None)
                vn_fixture = self.create_vn(vn_name=vn_id,
                                            vn_subnets=[vn_subnet])

            ip_fabric = vn[vn_id].get('ip_fabric',False)
            if ip_fabric:
                ip_fab_vn_obj = self.get_ip_fab_vn()
                assert vn_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)

            vn_fixtures[vn_id] = vn_fixture

        return vn_fixtures

    def setup_vmis(self, vn_fixtures, vmi=None):
        '''Setup VMIs
        Input vmi format:
            vmi = {'count':2,
                   'vmi1':{'vn': 'vn1'},
                   'vmi2':{'vn': 'vn1'},
                  }
        '''
        if vmi is None:
            vmi = {}
        vmi_count = vmi.pop('count', 0)
        vmi_fixtures = {} # Hash to store VMI fixtures
        vmi_keys = [each_key for each_key in vmi if re.match(r'vmi\d+',each_key)]
        for each_vmi in vmi_keys:
            vmi_id = each_vmi
            vmi_vn = vmi[vmi_id]['vn']
            vn_fixture = vn_fixtures[vmi_vn]
            vmi_fixture = self.setup_vmi(vn_fixture.uuid)
            if vmi[vmi_id].get('vip'):
                vIP = vmi[vmi_id]['vip']
                mode = vmi[vmi_id].get('mode', 'active-standby')
                self.config_aap(vmi_fixture, vIP, mac=vmi_fixture.mac_address,
                                aap_mode='active-active', contrail_api=True)

            vmi_fixtures[vmi_id] = vmi_fixture

        return vmi_fixtures

    def setup_vms(self, vn_fixtures, vmi_fixtures, vm=None, **kwargs):
        '''Setup VMs
        Input vm format:
            vm = {'count':2, 'launch_mode':'distribute',
                  'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                    'vlan': str(vmi['vmi3']['vlan'])} },
                  'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                    'vlan': str(vmi['vmi4']['vlan'])} }
                }
            launch_mode can be distribute or non-distribute
        '''
        if vm is None:
            vm = {}
        vm_count = vm.pop('count',0)
        image_name = kwargs.get('image_name','cirros')
        launch_mode = vm.get('launch_mode','default')
        vm_fixtures = {} # Hash to store VM fixtures

        compute_nodes = self.orch.get_hosts()
        compute_nodes_len = len(compute_nodes)
        index = random.randint(0,compute_nodes_len-1)
        vm_index = 0        
        vm_keys = [each_key for each_key in vm if re.match(r'vm\d+',each_key)]
        for each_vm in vm_keys:
            vm_id = each_vm
            vn_list = vm[vm_id]['vn']
            vmi_list = vm[vm_id]['vmi']

            vn_fix_obj_list =[]
            vmi_fix_uuid_list =[]

            # Build the VN fixtures objects
            for vn in vn_list:
                vn_fix_obj_list.append(vn_fixtures[vn].obj)

           # Build the VMI UUIDs
            for vmi in vmi_list:
                vmi_fix_uuid_list.append(vmi_fixtures[vmi].uuid)

            # VM launch mode handling
            # Distribute mode, generate the new random index
            # Non Distribute mode, use previously generated index
            # Default mode, Nova takes care of launching
            if self.inputs.orchestrator == 'vcenter':
                index = vm_index%compute_nodes_len
                node_name = compute_nodes[index]
                vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                        port_ids=vmi_fix_uuid_list,
                                        node_name=node_name, image_name='ubuntu')
            else:
                if launch_mode == 'distribute':
                    index = vm_index%compute_nodes_len
                    node_name = self.inputs.compute_names[index]
                elif launch_mode == 'non-distribute':
                    node_name = self.inputs.compute_names[index]
                elif launch_mode == 'default':
                    node_name=None

                vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                            port_ids=vmi_fix_uuid_list,
                                            node_name=node_name, image_name=image_name)
            vm_fixtures[vm_id] = vm_fixture
            vm_index = vm_index + 1 


        for vm_fixture in vm_fixtures.values():
            assert vm_fixture.wait_till_vm_is_up()

        return vm_fixtures

    def setup_lrs(self, lrs, vn_fixtures):
        '''Setup Logical routers
        Input LR format:
            LogicalRouter = {
                   'lr1':{'vn_list': ['vn1','vn2'], 'vni': '7001'},
                   'lr2':{'vn_list': ['vn3','vn4'], 'vni': '7002'},
                  }
        '''
        lr_fixtures = {} # Hash to store Logical router fixtures
         
        self.logger.info('Creating Logical Routers: %s'%(lrs))
        for each_lr in lrs:
            lr_fix_inputs = { 'name':each_lr, 'connections':self.connections }
            vn_uuid_list = [] 
            for each_vn in lrs[each_lr]['vn_list']:
                vn_uuid_list.append(vn_fixtures[each_vn].uuid)

            self.logger.info('Creating Logical Router: %s  with VN uuids: %s'%(each_lr, vn_uuid_list))
            lr_fix_inputs['connected_networks'] = {'vns': vn_uuid_list}

            if 'vni' in lrs[each_lr]:
                lr_fix_inputs['vni'] = lrs[each_lr]['vni']

            if 'vni' in lrs[each_lr]:
                lr_fix_inputs['vni'] = lrs[each_lr]['vni']
                
            lr_fixtures[each_lr] = self.useFixture(LogicalRouterFixture(**lr_fix_inputs))

        return lr_fixtures


    def setup_evpn_type5(self, vn=None, vmi=None, vm=None, lrs=None, verify=True):
        '''Setup EVPN Type5 forwarding

            Input parameters looks like:
                lr = {
                   'lr1':{'vn_list': ['vn1','vn2'], 'vni': '7001'},
                   'lr2':{'vn_list': ['vn3','vn4'], 'vni': '7002'},
                  }
                #VN parameters:
                vn = {'count':1,            # VN count
                     # VN Details
                    'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
                    'vn2':{'subnet':'20.20.20.0/24'},
                    }

                #VMI parameters:
                vmi = {'count':2, # VMI Count
                    'vmi1':{'vn': 'vn1'}, # VMI details
                    'vmi2':{'vn': 'vn1'}, # VMI details
                    }

                #VM parameters:
                vm = {'count':2, # VM Count
                    # VM Launch mode i.e distribute non-distribute, default
                    'launch_mode':'distribute',
                    'vm1':{'vn':['vn1'], 'vmi':['vmi1']}, # VM Details
                    'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # VM Details
                    }

        '''
        #This step is not required as default encapsulation order itself is vxlan,MPLSoverGRE,MPLSoverUDP
        self.update_encap_priority(['VXLAN', 'MPLSoUDP', 'MPLSoGRE'])

        self.vnc_h.enable_vxlan_routing()

        # VNs creation
        vn_fixtures = self.setup_vns(vn)

        # VMIs creation
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)

        # VMs creation
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm, image_name='ubuntu')

        #Setup Logical Routers
        self.logger.info('Logical Router Details %s ' %(lrs))
        lr_fixtures = self.setup_lrs(copy.deepcopy(lrs), vn_fixtures)

        # Extra sleep for BGP route updates between controller and fabric gw
        time = 30
        self.logger.info('Sleeping for %s secs for BGP convergence' %(time))
        self.sleep(time)

        ret_dict = {
            'vmi_fixtures':vmi_fixtures,
            'vn_fixtures':vn_fixtures,
            'vm_fixtures':vm_fixtures,
            'lr_fixtures':lr_fixtures,
        }
        return ret_dict

    def delete_auto_lr(self, fabric_name):
        lr_name = fabric_name + '-CRB-gateway-logical-router'
        lr_fq_name = ['default-domain', 'admin', lr_name]
        self.logger.info('Auto Logical Router fq name %s' %(lr_fq_name))
        self.vnc_h.delete_router(fq_name=lr_fq_name)


