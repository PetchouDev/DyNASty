from ipaddress import IPv4Network
from typing import Dict, Any, Tuple, List


def collect_routing_info(
    provider_devices: Dict[str, Any],
    provider_asn: int,
    client_routers: Dict[str, Any],
    subnets_info: List[Tuple[str, str, str, IPv4Network, int]]
) -> None:
    # OSPF/MPLS pour provider
    for name, dev in provider_devices.items():
        ospf_list: List[Dict[str, str]] = []
        mpls_list: List[str] = []
        for if_name, if_conf in dev['interfaces'].items():
            if if_conf['type'] == 'loopback':
                ospf_list.append({'address': if_conf['ip_address'], 'wildcard_mask': '0.0.0.0'})
            elif if_conf['type'] == 'backbone':
                # On suppose que les interfaces backbone sont MPLS
                sid = if_conf['subnet_id']
                subnet = next(s for (_,_,_,s,sid_) in subnets_info if sid_ == sid)
                ospf_list.append({'address': str(subnet.network_address), 'wildcard_mask': str(subnet.hostmask)})
                mpls_list.append(if_name)
        dev['ospf_subnets'] = ospf_list
        dev['mpls_interfaces'] = mpls_list
        # Pairs iBGP
        dev['iBGP_neighbors'] = [
            peer_dev['interfaces']['loopback0']['ip_address']
            for peer_dev in provider_devices.values()
            if peer_dev['role'] == 'edge' and peer_dev['hostname'] != name
        ]

    #  iBGP et Route-Reflector
    pe_loops = {
        name: dev['interfaces']['loopback0']['ip_address']
        for name, dev in provider_devices.items()
        if dev['role'] == 'edge'
    }
    rr_list = [
        name for name, dev in provider_devices.items()
        if dev.get('is_route_reflector')
    ]

    for name, dev in provider_devices.items():
        if not (dev['role'] == 'edge' or dev.get('is_route_reflector')):
            continue

        if dev.get('is_route_reflector'):
            peer_ips = [ip for peer, ip in pe_loops.items() if peer != name]
        else:
            if rr_list:
                peer_ips = [
                    provider_devices[rr]['interfaces']['loopback0']['ip_address']
                    for rr in rr_list if rr != name
                ]
            else:
                peer_ips = [ip for peer, ip in pe_loops.items() if peer != name]

        ibgp = {}
        for peer_ip in peer_ips:
            ibgp[peer_ip] = {
                'remote_as':              provider_asn,
                'update_source':          'Loopback0',
            }
        dev['iBGP_neighbors'] = ibgp

    #  eBGP vers les clients
    for dev in provider_devices.values():
        if dev['role'] != 'edge':
            continue

        ebgp = {}
        rd = 1
        dev['VRF'] = {}
        for if_conf in dev['interfaces'].values():
            if if_conf['type'] == 'client':
                # Trouver le client associé à l'interface
                peer_name  = if_conf['neighbors'][0]
                client_dev = client_routers[peer_name]

                #Récupération de l'IP de l'interface du client
                client_if = next(
                    ifc for ifc in client_dev['interfaces'].values()
                    if ifc['subnet_id'] == if_conf['subnet_id']
                )
                if not client_if:
                    raise ValueError(f"Client {peer_name} does not have an interface with subnet_id {if_conf['subnet_id']}")
                if not client_if['ip_address']:
                    raise ValueError(f"Client {peer_name} does not have an IP address assigned to subnet_id {if_conf['subnet_id']}")
                
                vrf_name = f"CLIENT_{client_dev['client']}_VRF"
                ebgp[client_if['ip_address']] = {
                    'BGP_asn': client_dev['BGP_asn'],
                    'VRF': vrf_name,
                }
                dev['VRF'][client_dev["BGP_asn"]] = {
                    'name': vrf_name,
                    'rd': rd,
                }
                rd += 1
        dev['eBGP_neighbors'] = ebgp

    # BGP des clients
    for name, c in client_routers.items():
        advert_nets = []
        for net in c.get('BGP_advertized_networks', []):
            nw = IPv4Network(net)
            advert_nets.append({
                'address': str(nw.network_address),
                'mask':    str(nw.netmask)
            })
        c['bgp_advertise'] = advert_nets

        peer_ip = next(
            ifc['ip_address']
            for p in provider_devices.values()
            for ifc in p['interfaces'].values()
            if name in ifc.get('neighbors', [])
        )
        c['eBGP_peer'] = {
            'ip_address': peer_ip,
            'BGP_asn':        provider_asn
        }
