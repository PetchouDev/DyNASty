

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from pprint import pprint
from traceback import format_exc
from typing import Any, Dict

from tools.devices_management import merge_and_tag_devices, normalize_interfaces, tag_interface_types
from tools.files_management import CONFIG_DIR, render_and_write
from tools.network_managment import add_loopback_interfaces, allocate_link_subnets, assign_ips_on_subnets, build_l2_links, format_client_BGP_networks
from tools.routing_management import collect_routing_info


def generate_configs(intention: Dict[str, Dict[str, Any]]) -> Path:
    provider_int = intention['provider']
    clients_int = intention['clients']

    # 1. Tag les types de routeurs (backbone, edge, client)
    prov_devs, cli_devs = merge_and_tag_devices(
        provider_int['routers'],
        clients_int,
        provider_int['BGP_asn'],
        provider_int.get('route_reflectors')
    )

    # 2. Normalisation des interfaces
    normalize_interfaces(prov_devs)
    normalize_interfaces(cli_devs)

    # 3. Loopbacks sur les PE
    add_loopback_interfaces(prov_devs, provider_int['loopback_range'])

    # 4. Tagger les types de liens (client: client <-> provider, provider: provider <-> provider)
    tag_interface_types(prov_devs, cli_devs)

    # 5. L2 links
    l2_links = build_l2_links(prov_devs, cli_devs)

    # 6. IPAM: allocation et assignation
    ipam_ranges = {
        'provider': provider_int['ip_range'],
        'client': clients_int['global']['ip_range']
    }
    subnets_info = allocate_link_subnets(l2_links, ipam_ranges)
    # fusion devices for assign
    all_devs = {**prov_devs, **cli_devs}
    assign_ips_on_subnets(all_devs, subnets_info)

    # 7. Collecte OSPF/BGP
    collect_routing_info(
        prov_devs,
        provider_int['BGP_asn'],
        cli_devs, 
        subnets_info
        )
    
    # 8. Formattage des réseau diffusés par les clients via BGP
    format_client_BGP_networks(cli_devs)

    # 9. Export des configurations
    all_devices = {
        'provider': prov_devs, 
        'clients': cli_devs, 
        'subnets': subnets_info,
    }
    out = CONFIG_DIR / 'devices.json'
    with open(out, 'w') as f:
        json.dump(all_devices, f, indent=4, default=str)
    
    # 10. Rendu des configurations
    templates = {
        'client': 'client_edge.j2',
        'edge': 'provider_edge.j2',
        'backbone': 'provider_bb.j2',
    }
    config_files: Dict[str, Path] = {}

    # Creation du répertoire de configuration s'il n'existe pas
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # pprint(prov_devs["PE1"])

    # Rendu et écriture des configurations en parallèle
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(render_and_write, name, details, templates): name
            for name, details in {**prov_devs, **cli_devs}.items()
        }
        for future in as_completed(futures):
            try:
                device_name = futures[future]
                config_files[device_name] = future.result()
            except Exception as e:
                print(f"Error generating config for {device_name}: {e}\n{format_exc()}")
    
    return config_files