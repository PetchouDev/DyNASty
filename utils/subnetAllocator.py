from ipaddress import ip_network

class SubnetAllocator:
    def __init__(self, base_network="10.0.0.0/8"):
        self.base_network = base_network
        self.reserved_subnets = []

    
    def get_subnets(self, subnets_intention=dict) -> dict:
        """
        Get the next available subnet of a specific number of hosts.
        """
        # Start with the biggest size and work downwards to avoid fragmentation
        subnets_id = sorted(subnets_intention.keys(), key=lambda x: subnets_intention[x]["size"], reverse=True)

        for sid in subnets_id:
            subnet_size = subnets_intention[sid]["size"]
            # Calculate the subnet size
            subnet_mask = 30
            while (2 ** (32- subnet_mask)) - 2 < subnet_size:
                subnet_mask -= 1

            # Find the next available subnet
            for subnet in ip_network(self.base_network).subnets(new_prefix=subnet_mask):
                # Check if the subnet is already reserved
                if not any(subnet.overlaps(reserved) for reserved in self.reserved_subnets):
                    # Reserve the subnet
                    self.reserved_subnets.append(subnet)
                    subnets_intention[sid]["subnet"] = subnet
                    break
            else:
                print(f"No available subnets for size {subnet_size}")

        return subnets_intention

# Test the SubnetAllocator class
if __name__ == "__main__":
    allocator = SubnetAllocator()
    sizes = {"0": 2, "1": 3, "2": 9} # {subnet_id: number of hosts to fit}
    subnets = allocator.get_subnets(sizes)
    print("Reserved subnets:")
    for subnet_id, subnet in subnets.items():
        print(f"Subnet ID {subnet_id}: {subnet}")
