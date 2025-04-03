import os
import json
from pathlib import Path
from ipaddress import IPv4Network

from jinja2 import Environment, FileSystemLoader
from gns3fy import Gns3Connector

PATH = Path(__file__).parent.resolve()
CONFIG_DIR = PATH / "data" / "configs"
TEMPLATES_DIR = PATH / "templates"

os.chdir(PATH)

from utils.fileDialog import FileDialog
from utils.projectSelector import ProjectSelector
from utils.subnetAllocator import SubnetAllocator

def generate_configs(intention: dict):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    provider_intention = intention["provider"]
    provider_ip_range = provider_intention["ip_range"]
    provider_devices = provider_intention["routers"]


    # Make a list of L2 links (P1, P2) for a bidirectional link, (P1, P2, P3, ...) if there is a switch between
    L2_links = []
    for device, details in provider_devices.items():
        # Set the default role of a router to "backbone"
        details["role"] = "backbone"
        details["hostname"] = device
        for interface, neighbors in details["interfaces"].items():
            if all(neighbor in provider_devices for neighbor in neighbors):
                L2_topology = [device] + (neighbors if isinstance(neighbors, list) else [neighbors])
            else:
                details["role"] = "edge"

                provider_neighbors = []
                for neighbor in neighbors:
                    if neighbor in provider_devices:
                        provider_neighbors.append(neighbor)

                if len(provider_neighbors) == 0:
                    continue

                L2_topology = [device] + (provider_neighbors if isinstance(provider_neighbors, list) else [provider_neighbors])
                

            # If this L2 link is not already in the list, add it
            for link in L2_links:
                if set(link) == set(L2_topology):
                    break
            else:
                L2_links.append(L2_topology)
    
    # Make a dict of required subnets
    i = 0
    subnets = {}
    for link in L2_links:
        # Get the size of the link
        size = len(link)

        subnets[i] = {"size": size, "subnet": None, "hosts": link}

        for host in link:
            if host not in provider_devices:
                continue
            # find the interface of the host that is connected to the link
            interface = None
            for interface_name, neighbors in provider_devices[host]["interfaces"].items():
                try:
                    if isinstance(neighbors, list):
                        if set(neighbors + [host]) == set(link):
                            interface = interface_name
                            break
                    elif set([host, neighbors]) == set(link):
                        interface = interface_name
                except TypeError:
                    pass # The subnet id is already assigned pushed, so the list became a dict and implicit conversion to a set raises a TypeError
                
            # push the subnet id to the host's interface
            if interface:
                provider_devices[host]["interfaces"][interface] = {
                    "neighbors": provider_devices[host]["interfaces"][interface],
                    "subnet_id": i
                }

            #provider_devices[host]["interfaces"][link[0]] = i
        i += 1

    # Allocate the subnets
    provider_allocator = SubnetAllocator(provider_ip_range)
    subnets = provider_allocator.get_subnets(subnets)

    # Build the subnets dict for interconnecting the clients to the provider
    # Retrieve params from the intention
    clients = intention["clients"]
    clients_ip_range = clients["global"]["ip_range"]
    client_allocator = SubnetAllocator(clients_ip_range)

    # Store the subnets for the clients
    client_subnets = {}

    # Iterate over the clients and their routers
    for client_name, details in clients.items():
        if client_name == "global":
            continue
        client_routers = details["routers"]
        for router, router_details in client_routers.items():
            router_details["hostname"] = router
            if router == "eBPG_asn":
                continue
            for interface, neighbor in router_details["interfaces"].items():
                client_subnets[i] = {
                    "hosts": [neighbor, router],
                    "subnet": None,
                    "size": 2
                }

                # Tag the subnet id to the routers interface
                client_routers[router]["interfaces"][interface] = {
                    "neighbors": neighbor,
                    "subnet_id": i
                }

                # Find the router in the provider devices and tag the subnet id to the interface
                for provider_router, provider_router_details in provider_devices.items():
                    for provider_interface, provider_interface_details in provider_router_details["interfaces"].items():
                        if isinstance(provider_interface_details, dict):
                            continue
                        if isinstance(provider_interface_details, list):
                            if router in provider_interface_details:
                                # Set the provider role to edge
                                provider_devices[provider_router]["role"] = "edge"

                                # Tag the subnet id to the provider interface
                                provider_devices[provider_router]["interfaces"][provider_interface] = {
                                    "neighbors": [router],
                                    "subnet_id": i
                                }
                                break
                        elif provider_interface_details == router:
                            # Set the provider role to edge
                            provider_devices[provider_router]["role"] = "edge"

                            # Tag the subnet id to the provider interface
                            provider_devices[provider_router]["interfaces"][provider_interface] = {
                                "neighbors": [router],
                                "subnet_id": i
                            }
                            break
                i += 1
                                
    # Allocate the subnets
    client_subnets = client_allocator.get_subnets(client_subnets)

    # Aggregate the subnets
    for k,v in client_subnets.items():
        subnets[k] = v

    # For each subnet, assign an IP address to each host
    for subnet_id, subnet in subnets.items():
        subnet_obj: IPv4Network = subnet["subnet"]
        hosts = subnet["hosts"].copy()

        subnet["hosts"] = {}

        allocated_addresses = []

        for host in hosts:
            for address in subnet_obj.hosts():
                if address not in allocated_addresses:
                    allocated_addresses.append(address)
                    subnet["hosts"][host] = address
                    break

    intention["subnets"] = subnets

    # Generate loopback addresses for the provider devices
    provider_loopback_range = provider_intention["loopback_range"]
    loopback_allocator = SubnetAllocator(provider_loopback_range)
    allocated_loopbacks = []
    for device, details in provider_devices.items():
        for address in IPv4Network(provider_loopback_range).hosts():
            if address not in allocated_loopbacks:
                allocated_loopbacks.append(address)
                

                provider_devices[device]["interfaces"]["loopback0"] = {
                    "neighbors": [],
                    "subnet_id": None,
                    "ip_address": address,
                    "subnet_mask": "255.255.255.255"
                }
                break

    # Iterate through the routers interfaces to get their IP addresses directly from the interface section
    for device, details in provider_devices.items():
        for interface, details in details["interfaces"].items():
            if "ip_address" in details:
                continue

            details["ip_address"]  = subnets[details["subnet_id"]]["hosts"][device]
            details["subnet_mask"] = subnets[details["subnet_id"]]["subnet"].netmask

    for client, details in clients.items():
        if client == "global":
            continue
        for device, details in details["routers"].items():
            for interface, details in details["interfaces"].items():
                if "ip_address" in details:
                    continue
                
                details["ip_address"] = subnets[details["subnet_id"]]["hosts"][device]
                details["subnet_mask"] = subnets[details["subnet_id"]]["subnet"].netmask

    # For each provider device interface, set a client to the one that owns the peer, set to None if peer is not a client
    # Also create a dict for eBGP neighbors
    for device, device_details in provider_devices.items():
        for interface, details in device_details["interfaces"].items():
            details["client"] = None
            for neighbor in details["neighbors"]:
                if neighbor in provider_devices:
                    continue
                else:
                    # Find the client that owns the peer
                    for client, client_details in clients.items():
                        if client == "global":
                            continue
                        for client_router, client_router_details in client_details["routers"].items():
                            if neighbor == client_router:
                                details["client"] = client
                                # Find the interface of the client that is connected to the link
                                eBGP_client_interface = None
                                for client_interface, client_interface_details in client_router_details["interfaces"].items():
                                    if client_interface_details["neighbors"] == device:
                                            eBGP_client_interface = client_interface_details
                                            break
                                # Set the eBGP neighbor for the provider device
                                if eBGP_client_interface:
                                    if "eBGP_neighbors" not in device_details:
                                        device_details["eBGP_neighbors"] = {}
                                    device_details["eBGP_neighbors"][str(eBGP_client_interface["ip_address"])] = {
                                        "asn": client_router_details["eBGP_asn"],
                                        "VRF": "CLIENT_" + client + "_VRF"
                                    }
                                    client_router_details["eBGP_peer"] = {
                                        "ip_address": str(eBGP_client_interface["ip_address"]),
                                        "asn": provider_intention["BGP_asn"]
                                    }
                                break
                        else:
                            continue
                        break

    # For provider devices, generate the OSPF and MPLS configurations
    for device, device_details in provider_devices.items():
        # Get the subnets of each interface
        ospf_subnets = []
        mpls_interfaces = []

        for interface, details in device_details["interfaces"].items():
            if interface == "loopback0":
                ospf_subnets.append({"address": details["ip_address"], "wildcard_mask": "0.0.0.0"})
            else: 
                # If there is a client, do not enable OSPF on the interface
                
                # Do not enable OSPF or MPLS if there is a router in the L2 link that is not a provider device
                for neighbor in details["neighbors"]:
                    if not neighbor in provider_devices:
                        break
                    else:
                        interface_subnet = subnets[details["subnet_id"]]["subnet"]
                        ospf_subnets.append({"address": interface_subnet.network_address, "wildcard_mask": interface_subnet.hostmask})
                        mpls_interfaces.append(interface)

        device_details["ospf_subnets"] = ospf_subnets
        device_details["mpls_interfaces"] = mpls_interfaces

    # For edge devices, generate the BGP configurations
    for device, device_details in provider_devices.items():
        device_details["BGP_asn"] = provider_intention["BGP_asn"]
        if device_details["role"] == "edge":
            # Get the subnets of each interface
            other_edge_routers = []

            for other, other_details in provider_devices.items():
                if other == device:
                    continue
                if other_details["role"] == "edge":
                    other_edge_routers.append(other_details["interfaces"]["loopback0"]["ip_address"])           
                    

            device_details["iBGP_neighbors"] = other_edge_routers

    # Build the VRF for each client
    route_distinguisher = 1
    provider_intention["VRF"] = {}
    for client, details in clients.items():
        if client == "global":
            continue
        provider_intention["VRF"][client] = {
            "rd": route_distinguisher,
            "name": f"CLIENT_{client}_VRF",
        }
        route_distinguisher += 1

    # attach the VRF to the edge devices
    for device, device_details in provider_devices.items():
        if device_details["role"] == "edge":
            device_details["VRF"] = provider_intention["VRF"]

    # For each client, edit the eBGP_advertized_networks from CIDR to netmask
    # Do the same thing for unmanaged interfaces config
    for client, details in clients.items():
        if client == "global":
            continue
        for router, router_details in details["routers"].items():
            networks = router_details["eBGP_advertized_networks"]
            for i in range(len(networks)):
                # Convert the CIDR to netmask
                network = IPv4Network(networks[i])
                networks[i] = {
                    "address": network.network_address,
                    "mask": network.netmask
                }
            for interface, interface_subnet in router_details["unmanaged_interfaces"].items():
                # Convert the CIDR to netmask
                ip_address, subnet_mask = interface_subnet.split("/")
                # Convert the CIDR to netmask
                fake_network = IPv4Network(f"0.0.0.0/{subnet_mask}")

                router_details["interfaces"][interface] = {
                    "ip_address": ip_address,
                    "subnet_mask": fake_network.netmask
                }

    # with open(CONFIG_DIR / "details.json", "w") as f: # For debugging purposes
    #     json.dump(intention, f, indent=4, default=str)

    # Generate the configurations for each device
    for device, details in provider_devices.items():
        if details["role"] == "backbone":
            template_file = "provider_bb.j2"
        else:
            template_file = "provider_edge.j2"

        # Convert the IPv4Network object to strings
        details_dict = json.loads(json.dumps(details, default=str))
        config = env.get_template(template_file).render(details_dict)

        # Write the configuration to a file
        with open(CONFIG_DIR / f"{device}.cfg", "w") as f:
            f.write(config)

    for client, details in clients.items():
        if client == "global":
            continue
        for router, router_details in details["routers"].items():
            template_file = "client_edge.j2"
            # Convert the IPv4Network object to strings
            details_dict = json.loads(json.dumps(router_details, default=str))
            config = env.get_template(template_file).render(details_dict)

            # Write the configuration to a file
            with open(CONFIG_DIR / f"{router}.cfg", "w") as f:
                f.write(config)

# Example usage
if __name__ == "__main__":

    # Get the intention file
    file_dialog = FileDialog()
    selected_file = file_dialog.select_json_file()

    if selected_file:
        print(f"Selected file: {selected_file}")
    else:
        print("No file selected. Exiting.")
        exit()

    with open(selected_file, "r") as f:
        data = json.load(f)
    
    generate_configs(data)

    print(f"Configurations saved to {CONFIG_DIR}.")

    # Open the file explorer to the config directory
    os.startfile(str(CONFIG_DIR))

    # Automatically push the configs to GNS3 (not implemented yet)
    exit()
    server = Gns3Connector("http://localhost:3080", user="admin", cred="admin")
    selector = ProjectSelector(server)
    project = selector.get_project("NADS")
    
    if project:
        print(f"Selected project: {project.name}")
        print(project.nodes)
    else:
        print("No project selected. Exiting.")
