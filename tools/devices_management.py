from typing import Dict, Any, List, Tuple, Union

from tools.network_managment import CIDR_to_network

def merge_and_tag_devices(
    provider_devices: Dict[str, Any],
    clients: Dict[str, Any],
    provider_asn: int,
    route_reflector_list: Union[List[str], str, None]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Sépare et tague les devices :
        - role: 'backbone' | 'edge' | 'client'
        - is_route_reflector: True si dans la liste
        - hostname, BGP_asn
    """
    # 1. On normalise la liste des RRs
    if isinstance(route_reflector_list, str):
        rr_list = [route_reflector_list]
    elif isinstance(route_reflector_list, list):
        rr_list = route_reflector_list
    else:
        rr_list = []

    # 2. Tag des provider
    for name, details in provider_devices.items():
        # rôle edge/backbone
        is_edge = any(
            nbr not in provider_devices
            for iface in details.get('interfaces', {}).values()
            for nbr in (iface if isinstance(iface, list) else [iface])
        )
        details['role']                = 'edge' if is_edge else 'backbone'
        details['hostname']            = name
        details['BGP_asn']             = provider_asn
        details['is_route_reflector'] = name in rr_list

    # 3. Extraction et tag des clients
    client_routers: Dict[str, Any] = {}
    for client_name, c_data in clients.items():
        if client_name == 'global':
            continue
        for router, r_details in c_data.get('routers', {}).items():
            r_details['role']     = 'client'
            r_details['hostname'] = router
            r_details['client']   = client_name
            client_routers[router] = r_details

    return provider_devices, client_routers

def normalize_interfaces(devices: Dict[str, Any]) -> None:
    """
    Unifie tous les formats d'interface en dict avec clefs:
    neighbors (list[str]), subnet_id, ip_address, subnet_mask
    Modifie in-place.
    """
    for dev_name, dev in devices.items():
        new_if = {}
        for if_name, conf in dev.get('interfaces', {}).items():
            if isinstance(conf, dict):
                # conserve champs existants
                neighbors = conf.get('neighbors', [])
                new_if[if_name] = {
                    'neighbors': neighbors if isinstance(neighbors, list) else [neighbors],
                    'subnet_id': conf.get('subnet_id'),
                    'ip_address': conf.get('ip_address'),
                    'subnet_mask': conf.get('subnet_mask')
                }
            else:
                # chaine ou liste
                nbrs = conf if isinstance(conf, list) else [conf]
                new_if[if_name] = {
                    'neighbors': nbrs,
                    'subnet_id': None,
                    'ip_address': None,
                    'subnet_mask': None
                }
        dev['interfaces'] = new_if

        if dev["role"] == "client":
            for iface_name, network in dev.get('unmanaged_interfaces', {}).items():
                network = CIDR_to_network(network)
                dev['interfaces'][iface_name] = {
                    'neighbors': [],
                    'subnet_id': -1,
                    'ip_address': network['address'],
                    'subnet_mask': network['mask']
                }


def tag_interface_types(
    provider_devices: Dict[str, Any],
    client_devices: Dict[str, Any]
) -> None:
    """
    Ajoute champ 'type' à chaque interface après normalisation.
    """
    all_provs = set(provider_devices)
    for dev, details in provider_devices.items():
        for if_name, if_conf in details['interfaces'].items():
            if if_name == 'loopback0':
                if_conf['type'] = 'loopback'
            else:
                zone = 'backbone' if all(n in all_provs for n in if_conf['neighbors']) else 'client'
                if_conf['type'] = zone
                # Si c'est un lien vers un client, récupérer le nom du client
                if zone == 'client':
                    for c_dev, c_details in client_devices.items():
                        if c_dev in if_conf['neighbors']:
                            if_conf['client'] = c_details['client']
                            break

    for dev, details in client_devices.items():
        for if_name, if_conf in details['interfaces'].items():
            if if_name == 'loopback0':
                if_conf['type'] = 'loopback'
            else:
                # On suppose que les clients n'ont que des liens vers le provider
                if_conf['type'] = 'provider'
