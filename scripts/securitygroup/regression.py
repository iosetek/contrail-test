import os
import fixtures
import testtools
import unittest

from testresources import ResourcedTestCase

from connections import ContrailConnections
from securitygroup.config import ConfigSecGroup
from tcutils.wrappers import preposttest_wrapper
from securitygroup.setup import SecurityGroupSetupResource
from verify import VerifySecGroup
from policy.config import ConfigPolicy
from sdn_topo_setup import *
from topo_helper import *
import sdn_sg_test_topo
from tcutils.traffic import *
from time import sleep


class SecurityGroupRegressionTests(testtools.TestCase, ResourcedTestCase,
                                   fixtures.TestWithFixtures,
                                   ConfigSecGroup, VerifySecGroup):

    resources = [('base_setup', SecurityGroupSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SecurityGroupSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.inputs.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture

    def __del__(self):
        self.logger.debug("Unconfig the common resurces.")
        SecurityGroupSetupResource.finishedWith(self.res)

    def setUp(self):
        super(SecurityGroupRegressionTests, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        self.logger.debug("Tearing down SecurityGroupRegressionTests.")
        super(SecurityGroupRegressionTests, self).tearDown()
        SecurityGroupSetupResource.finishedWith(self.res)

    def runTest(self):
        pass

    def config_policy_and_attach_to_vn(self, rules):
        policy_name = "sec_grp_policy"
        policy_fix = self.config_policy(policy_name, rules)
        assert policy_fix.verify_on_setup()
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.res.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.res.vn2_fix)

    @preposttest_wrapper
    def test_sec_group_with_proto(self):
        """Verify security group with allow specific protocol on all ports and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto()
        return True

    @preposttest_wrapper
    def test_sec_group_with_port(self):
        """Verify security group with allow specific protocol/port and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 9000}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_port_proto(port_test=True)
        return True

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp(self):
        """Verify security group with allow specific protocol on all ports and policy with allow only TCP between VN's"""
        self.logger.info("Configure the policy with allow TCP only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp()
        return True

    @preposttest_wrapper
    def test_sec_group_with_proto_and_policy_to_allow_only_tcp_ports(self):
        """Verify security group with allow specific protocol on all ports and policy with allow only TCP on specifif ports between VN's"""
        self.logger.info(
            "Configure the policy with allow TCP port 8000/9000 only rule.")
        rules = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'source_network': self.res.vn1_name,
                'src_ports': [8000, 8000],
                'dest_network': self.res.vn2_name,
                'dst_ports': [9000, 9000],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)

        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)

        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)

        self.verify_sec_group_with_udp_and_policy_with_tcp_port()
        return True

    @preposttest_wrapper
    def test_vn_compute_sg_comb(self):
        """ Verify traffic between intra/inter VN,intra/inter compute and same/diff default/user-define SG"""
        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_4vn_xvm_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password, compute_node_list=self.inputs.compute_ips)
        except (AttributeError,NameError):
            topo = topology_class_name(compute_node_list=self.inputs.compute_ips)

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify_negative_cases(topo_obj, config_topo)
        return True
    #end test_vn_compute_sg_comb

    @preposttest_wrapper
    def test_sec_group_with_proto_double_rules_sg1(self):
        """Verify security group with allow tcp/udp protocol on all ports and policy with allow all between VN's"""
        self.logger.info("Configure the policy with allow any")
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.res.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.res.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        self.config_policy_and_attach_to_vn(rules)
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg1_fix.replace_rules(rule)
        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.res.sg2_fix.replace_rules(rule)
        self.verify_sec_group_port_proto(double_rule=True)
        return True
#end test_sec_group_with_proto_double_rules_sg1

    @preposttest_wrapper
    def test_sg_stateful(self):
        """ Test if SG is stateful:
        1. test if inbound traffic without allowed ingress rule is allowed
        2. Test if outbound traffic without allowed egress rule is allowed
        3. test traffic betwen SG with only ingress/egress rule"""

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo_sg_stateful(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except (AttributeError,NameError):
            topo.build_topo_sg_stateful()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=False)
        return True
    #end test_sg_stateful

    @preposttest_wrapper
    def test_sg_multiproject(self):
        """ Test SG across projects"""

        topology_class_name = None

        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config_multiproject

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))

        topo = topology_class_name()
        self.topo = topo

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        topo_objs = {}
        config_topo = {}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup()
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo_objs, config_topo, vm_fip_info = out['data']

        self.start_traffic_and_verify_multiproject(topo_objs, config_topo, traffic_reverse=False)

        return True

    @preposttest_wrapper
    def test_sg_no_rule(self):
        '''Test SG without any rule:
           it should deny all traffic'''

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_1vn_2vm_config

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except (AttributeError,NameError):
            topo.build_topo()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        self.start_traffic_and_verify(topo_obj, config_topo, traffic_reverse=True)

        return True
        #end test_sg_no_rule

    @preposttest_wrapper
    def test_icmp_error_handling1(self):
        """ Test ICMP error handling
	1. ingress-udp from same SG, egress-all
	2. Test with SG rule, ingress-egress-udp only
	3. Test with SG rule, ingress-egress-all"""

        topology_class_name = None

        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except (AttributeError,NameError):
            topo.build_topo()
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

	#Test SG rule, ingress-udp same SG, egress-all 
	port = 10000
	pkt_cnt = 10
	src_vm_name = 'vm1'
	dst_vm_name = 'vm3'
	src_vm_fix = config_topo['vm'][src_vm_name]
	dst_vm_fix = config_topo['vm'][dst_vm_name]
	src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]

	#start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)
	#start traffic
	start_traffic_pktgen_between_vm(self, src_vm_fix, dst_vm_fix, dest_min_port = port,
						dest_max_port = port)	
	#verify packet count and stop tcpdump
	assert stop_tcpdump_on_vm_verify_cnt(self, session, pcap)
	#stop traffic
	stop_traffic_pktgen(self, src_vm_fix)

	#Test with SG rule, ingress-egress-udp only
        rule = [{'direction': '>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
	config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)
        #start traffic
        start_traffic_pktgen_between_vm(self, src_vm_fix, dst_vm_fix, dest_min_port = port,
                                                dest_max_port = port)
        #verify packet count and stop tcpdump
        assert stop_tcpdump_on_vm_verify_cnt(self, session, pcap)
        #stop traffic
        stop_traffic_pktgen(self, src_vm_fix)

        #Test with SG rule, ingress-egress-all
	dst_vm_fix = config_topo['vm']['vm2']
        rule = [{'direction': '>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)
        #start traffic
        start_traffic_pktgen_between_vm(self, src_vm_fix, dst_vm_fix, dest_min_port = port,
                                                dest_max_port = port)
        #verify packet count and stop tcpdump
        assert stop_tcpdump_on_vm_verify_cnt(self, session, pcap)
        #stop traffic
        stop_traffic_pktgen(self, src_vm_fix)


        return True
    #end test_icmp_error_handling1 

    @preposttest_wrapper
    def test_icmp_error_handling2(self):
        """
	1. Test ICMP error handling with SG rules egress-udp only
	2. Test ICMP error from agent"""

        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
		compute_node_list=self.inputs.compute_ips)
        except (AttributeError,NameError):
            topo.build_topo2(compute_node_list=self.inputs.compute_ips)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        #Test with SG rule, egress-udp only 
        port = 10000
        pkt_cnt = 10
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]

	dst_vm_fix.remove_security_group(secgrp='default')
        #start tcpdump on src VM
        filters = '\'(icmp[0]=3 and icmp[1]=3 and src host %s and dst host %s)\'' % (dst_vm_fix.vm_ip, src_vm_fix.vm_ip)
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)
        #start traffic
        start_traffic_pktgen_between_vm(self, src_vm_fix, dst_vm_fix, dest_min_port = port,
                                                dest_max_port = port)
        #verify packet count and stop tcpdump
        assert stop_tcpdump_on_vm_verify_cnt(self, session, pcap)
        #stop traffic
        stop_traffic_pktgen(self, src_vm_fix)

	#Test ICMP error from agent
	if len(self.inputs.compute_ips) < 2:
	    self.logger.info("Skipping second case(Test ICMP error from agent), \
				    this test needs atleast 2 compute nodes")
	    raise self.skipTest("Skipping second case(Test ICMP error from agent), \
				    this test needs atleast 2 compute nodes")
	    return True
        rule = [{'direction': '>',
                'protocol': 'icmp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'icmp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        config_topo['sec_grp'][topo_obj.sg_list[0]].replace_rules(rule)

	self.logger.info("increasing MTU on src VM and ping with bigger size and then revert back MTU")
	cmd_ping = 'ping -M want -s 2500 -c 10 %s | grep \"Frag needed and DF set\"' % (dst_vm_fix.vm_ip)
	cmds = ['ifconfig eth0 mtu 3000', cmd_ping, 'ifconfig eth0 mtu 1500'] 
        output = src_vm_fix.run_cmd_on_vm(cmds=cmds, as_sudo=True)
	
	self.logger.info("output for ping cmd: %s" % output[cmd_ping])
	if not "Frag needed and DF set" in output[cmd_ping]:
	    self.logger.error("expected ICMP error for type 3 code 4 not found")
	    return False

	return True
	#end test_icmp_error_handling2

    @preposttest_wrapper
    def test_icmp_error_handling_from_mx_with_si(self):
        """ Test ICMP error handling from MX with SI in the middle
	1. uses traceroute util on the VM"""

	if ('MX_GW_TEST' not in os.environ) or (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') != '1')):
            self.logger.info(
                "Skiping Test. Env variable MX_GW_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_GW_TEST is not set. Skipping the test")
	    return True

	public_vn_info = {'subnet':[self.inputs.fip_pool], 'router_asn':self.inputs.router_asn, 'rt_number':self.inputs.mx_rt}
        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_mx_with_si

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                public_vn_info=public_vn_info)
        except (AttributeError,NameError):
            topo.build_topo(public_vn_info=public_vn_info)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(skip_verify='no')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

	pol_fix = config_topo['policy'][topo_obj.policy_list[0]]
	policy_id = pol_fix.policy_obj['policy']['id']

	new_policy_entries = config_topo['policy'][topo_obj.policy_list[1]].policy_obj['policy']['entries']
        data = {'policy': {'entries': new_policy_entries}}
	pol_fix.update_policy(policy_id, data)

	src_vm_name = 'vm2'
	src_vm_fix = config_topo['vm'][src_vm_name]
	src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]
	pkg = 'traceroute_2.0.18-1_amd64.deb'

        self.logger.info("copying traceroute pkg to the compute node.")
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
            path = self.inputs.test_repo_dir + '/scripts/tcutils/pkgs/' + pkg
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (self.inputs.username,
                 src_vm_fix.vm_node_ip),
                password=self.inputs.password,
                src=path,
                dest='/tmp')

	self.logger.info("copying traceroute from compute node to VM")
        with settings(host_string='%s@%s' % (self.inputs.username, src_vm_fix.vm_node_ip),
                      password=self.inputs.password, warn_only=True, abort_on_prompts=False):
	    path = '/tmp/' + pkg
            output = fab_put_file_to_vm(
                host_string='%s@%s' %
                (src_vm_fix.vm_username,
                 src_vm_fix.local_ip),
                password=src_vm_fix.vm_password,
                src=path,
                dest='/tmp')

        self.logger.info("installing traceroute")
        cmd = 'dpkg -i /tmp/' + pkg
        output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert "Setting up traceroute" in output_cmd_dict[cmd], "traceroute pkg installation error, output:%s" % output_cmd_dict[cmd]

        self.logger.info("starting tcpdump on src VM")
        filters = '\'(icmp[0]=11 and icmp[1]=0)\'' 
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)

	self.logger.info("starting traceroute to out of cluster, 8.8.8.8")
	cmd = 'traceroute 8.8.8.8'
	for i in range(0,4):
            output_cmd_dict = src_vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
	    self.logger.info(output_cmd_dict[cmd])

            if stop_tcpdump_on_vm_verify_cnt(self, session, pcap):
		return True

	return False 
	#end test_icmp_error_handling_from_mx_with_si

    @preposttest_wrapper
    def test_icmp_error_payload_matching(self):
        """ Test ICMP error handling with payload diff. from original packet
	1. icmp pakcet with payload matching should be accepted and others should be denied"""

        topology_class_name = None
        #
        # Get config for test from topology
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_icmp_error_handling

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))
        topo = topology_class_name()
        try:
            # provided by wrapper module if run in parallel test env
            topo.build_topo2(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password,
                compute_node_list=self.inputs.compute_ips)
        except (AttributeError,NameError):
            topo.build_topo2(compute_node_list=self.inputs.compute_ips)
        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        #Test with SG rule, egress-udp only and also send diff ICMP error with diff payload
        port = 10000
        pkt_cnt = 10
        src_vm_name = 'vm1'
        dst_vm_name = 'vm2'
        src_vm_fix = config_topo['vm'][src_vm_name]
        dst_vm_fix = config_topo['vm'][dst_vm_name]
        src_vn_fix = config_topo['vn'][topo_obj.vn_of_vm[src_vm_name]]

        dst_vm_fix.remove_security_group(secgrp='default')
        #start tcpdump on src VM
        filters = 'icmp' 
        session, pcap = start_tcpdump_on_vm(self, src_vm_fix, src_vn_fix, filters = filters)
        #start traffic
        start_traffic_pktgen_between_vm(self, src_vm_fix, dst_vm_fix, dest_min_port = port,
                                                dest_max_port = port)

        for icmp_type in xrange(0,3):
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=0,count=1)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count in ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                assert recv == 0, "recv count in not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

	#type 3 , code (0,15)
        for icmp_code in xrange(0,16):
	        sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
					port, port, payload="payload",
					icmp_type=3, icmp_code=icmp_code,count=1)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count in ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                assert recv == 0, "recv count in not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)

	#type (4,11), code 0
        for icmp_type in xrange(4,12):
                sender, receiver = self.start_traffic_scapy(dst_vm_fix, src_vm_fix, 'icmp',
                                        port, port, payload="payload",
                                        icmp_type=icmp_type, icmp_code=0,count=1)
                sent, recv = self.stop_traffic_scapy(sender, receiver)
                assert sent != 0, "sent count in ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)
                assert recv == 0, "recv count in not ZERO for icmp type %s and code %s" % (icmp_type, icmp_code)


        #verify packet count and stop tcpdump
        assert stop_tcpdump_on_vm_verify_cnt(self, session, pcap)
        #stop traffic
        stop_traffic_pktgen(self, src_vm_fix)

        return True
        #end test_icmp_error_payload_matching 

