from ipaddress import IPv4Network
from typing import Dict, Any, List, Tuple

from lib.subnetAllocator import SubnetAllocator


def CIDR_to_network(cidr: str) -> str:
    """
    Convertit un CIDR en masque de sous-réseau.
    """
    try:
        address, mask = cidr.split('/')
        mask = "1" * int(mask) + "0" * (32 - int(mask))
        mask_str = '.'.join(str(int(mask[i:i + 8], 2)) for i in range(0, 32, 8))
        return {
            "address": address,
            "subnet_mask": mask_str,
            "cidr": cidr
        }
    except ValueError as e:
        raise ValueError(f"Invalid CIDR notation: {cidr}") from e

def build_l2_links(
    provider_devices: Dict[str, Any],
    client_routers: Dict[str, Any]
) -> List[Tuple[str, str, str]]:
    """
    Liste de liens L2: (dev1, dev2, zone)
    """
    edges: List[Tuple[str, str, str]] = []
    seen = set()
    all_devices = {**provider_devices, **client_routers}
    for dev, details in all_devices.items():
        for if_name, if_conf in details.get('interfaces', {}).items():
            for nbr in if_conf['neighbors']:
                key = frozenset({dev, nbr})
                if dev == nbr or key in seen:
                    continue
                seen.add(key)
                zone = 'provider' if dev in provider_devices and nbr in provider_devices else 'client'
                edges.append((dev, nbr, zone))
    return edges

def add_loopback_interfaces(
    provider_devices: Dict[str, Any],
    loopback_range: str
) -> None:
    """
    Ajoute loopback0 aux devices role 'edge'.
    """
    allocated = set()
    for name, dev in provider_devices.items():
        for addr in IPv4Network(loopback_range).hosts():
            if addr not in allocated:
                allocated.add(addr)
                dev['interfaces']['loopback0'] = {
                    'neighbors': [],
                    'subnet_id': None,
                    'ip_address': str(addr),
                    'subnet_mask': '255.255.255.255',
                    'type': 'loopback'
                }
                break

def allocate_link_subnets(
    l2_links: List[Tuple[str, str, str]],
    ipam_ranges: Dict[str, str]
) -> List[Tuple[str, str, str, IPv4Network, int]]:
    """
    Alloue un sous-réseau par lien L2.
    Retourne une liste de tuples (dev1, dev2, zone, subnet, id).
    """
    allocators = {zone: SubnetAllocator(cidr) for zone, cidr in ipam_ranges.items()}
    subnets_info: List[Tuple[str, str, str, IPv4Network, int]] = []
    for idx, (d1, d2, zone) in enumerate(l2_links):
        allocator = allocators.get(zone)
        if not allocator:
            continue
        # intention taille 2 hôtes
        intention = {0: {'hosts': [d1, d2], 'size': 2, 'subnet': None}}
        allocated = allocator.get_subnets(intention)
        subnet = allocated[0]['subnet']
        subnets_info.append((d1, d2, zone, subnet, idx))
    return subnets_info

def assign_ips_on_subnets(
    devices: Dict[str, Any],
    subnets_info: List[Tuple[str, str, str, IPv4Network, int]]
) -> None:
    """
    Assigne IPs et masque aux interfaces en fonction des subnets_info,
    et renseigne 'subnet_id', 'ip_address', 'subnet_mask' dans devices.
    """
    for d1, d2, _, subnet, sid in subnets_info:
        hosts = [d1, d2]
        assigned = {}
        for ip in subnet.hosts():
            if len(assigned) < 2:
                assigned[hosts[len(assigned)]] = ip
            else:
                break
        # assignation sur chaque interface
        for dev, peer in ((d1, d2), (d2, d1)):
            for if_name, if_conf in devices[dev]['interfaces'].items():
                if peer in if_conf['neighbors']:
                    if_conf['subnet_id'] = sid
                    if_conf['ip_address'] = str(assigned[dev])
                    if_conf['subnet_mask'] = str(subnet.netmask)
        hosts = [d1, d2]
        assigned = {}
        for ip in subnet.hosts():
            if len(assigned) < 2:
                assigned[hosts[len(assigned)]] = ip
            else:
                break
        # assignation sur chaque interface
        for dev, peer in ((d1, d2), (d2, d1)):
            for if_name, if_conf in devices[dev]['interfaces'].items():
                if peer in if_conf['neighbors']:
                    if_conf['subnet_id'] = sid
                    if_conf['ip_address'] = str(assigned[dev])
                    if_conf['subnet_mask'] = str(subnet.netmask)

def format_client_BGP_networks(
    client_routers: Dict[str, Any],
) -> None:
    """
    Formate les réseaux BGP des clients.
    Convertit les réseaux CIDR en dictionnaire avec adresse, masque et CIDR.
    """
    for name, dev in client_routers.items():
        for i in range(len(dev['BGP_advertized_networks'])):
            cidr = dev['BGP_advertized_networks'][i]
            try:
                network_info = CIDR_to_network(cidr)
                dev['BGP_advertized_networks'][i] = network_info
            except ValueError as e:
                print(f"Error processing BGP network {cidr} for device {name}: {e}")
