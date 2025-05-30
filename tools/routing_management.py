from ipaddress import IPv4Network
from typing import Dict, Any, Tuple, List


def collect_routing_info(
    provider_devices: Dict[str, Any],
    provider_asn: str,
    client_routers: Dict[str, Any],
    subnets_info: List[Tuple[str, str, str, IPv4Network, int]]
) -> None:
    """
    Construit et ajoute pour chaque device :
        - ospf_subnets : liste des {address, wildcard_mask}
        - mpls_interfaces : liste des noms d'interface
        - iBGP_neighbors : liste d'IP de loopbacks autres PE
        - eBGP_neighbors : dict peer_ip -> {asn, VRF}
        - bgp_advertise (pour clients) : liste des réseaux à annoncer
    Modifie provisoirement provider_devices & client_routers.
    """
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

    # eBGP pour provider & collection des réseaux clients
    for c in client_routers.values():
        # Construction des réseaux à annoncer
        for net in c.get('eBGP_advertized_networks', []):
            nw = IPv4Network(net)
            c.setdefault('bgp_advertise', []).append({'address': str(nw.network_address), 'mask': str(nw.netmask)})
    for name, dev in provider_devices.items():
        dev["VRF"] = {}
        ebgp: Dict[str, Any] = {}
        route_distinguisher = 1
        for if_conf in dev['interfaces'].values():
            if if_conf['type'] == 'client':
                peer = if_conf['neighbors'][0]
                peer_dev = client_routers[peer]
                VRF_name = f"CLIENT_{peer_dev['client']}_VRF"
                ebgp[if_conf['ip_address']] = {
                    'BGP_asn': peer_dev['BGP_asn'],
                    'VRF': VRF_name,
                }
                # Assigner un route distinguisher unique pour chaque client
                dev["VRF"][peer_dev['client']] = {
                    'name': VRF_name,
                    'rd': route_distinguisher
                }
                # Incrémenter le route distinguisher pour le prochain client
                route_distinguisher += 1

        dev['eBGP_neighbors'] = ebgp
    
    # Pairs eBGP pour les clients
    for name, c in client_routers.items():
        peer_ip = next(
            d['interfaces'][iface]['ip_address']
            for d in provider_devices.values()
            for iface, ifc in d['interfaces'].items()
            if name in ifc['neighbors']
        )
        c['eBGP_peer'] = {
            'ip_address': peer_ip, 
            'BGP_asn': provider_asn,
        }
        # Réseaux diffusés par le client via eBGP déjà renseignés dans le fichier d'intention
