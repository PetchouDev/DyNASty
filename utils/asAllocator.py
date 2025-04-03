class asAllocator:
    def __init__(self):
        self.as_numbers = {}
        self.next_as_number = 1

    def allocate_as_number(self, client_id):
        if client_id not in self.as_numbers:
            self.as_numbers[client_id] = self.next_as_number
            self.next_as_number += 1
        return self.as_numbers[client_id]