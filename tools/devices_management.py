from typing import Dict, Any, Tuple


def merge_and_tag_devices(
    provider_devices: Dict[str, Any],
    provider_asn: str,
    clients: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Tag et sépare provider vs client routers.
    """
    # Tag provider
    for name, details in provider_devices.items():
        is_edge = any(
            (nbr not in provider_devices)
            for iface in details.get('interfaces', {}).values()
            for nbr in (iface if isinstance(iface, list) else [iface])
        )
        details['role'] = 'edge' if is_edge else 'backbone'
        details['hostname'] = name
        details['BGP_asn'] = provider_asn

    # Collect client routers
    client_routers: Dict[str, Any] = {}
    for client_name, c_data in clients.items():
        if client_name == 'global':
            continue
        for router, r_details in c_data.get('routers', {}).items():
            r_details['role'] = 'client'
            r_details['client'] = client_name
            r_details['hostname'] = router
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
