import telnetlib
import time

class TelnetClient:
    def __init__(self, host, port=23, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connection = None

    def connect(self):
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, self.timeout)
            print(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to {self.host}:{self.port} - {e}")

    def send_command(self, command):
        if self.connection:
            try:
                self.connection.write(command.encode('ascii') + b"\r\n")
                self.connection.read_until(b"#", timeout=self.timeout)
                response = self.connection.read_very_eager().decode('ascii')
                return response
            except Exception as e:
                print(f"Failed to send command '{command}' - {e}")
                return None
        else:
            print("No connection established.")
            return None

    def close(self):
        if self.connection:
            self.connection.close()
            print("Connection closed.")

    def push_configuration(self, config_commands:str):
        if not self.connection:
            self.connect()
        if self.connection:
            try:
                for command in config_commands.splitlines():
                    self.send_command(command.strip())
                    self.send_command("")
            except Exception as e:
                print(f"Failed to push configuration - {e}")
            finally:
                self.close()
        else:
            print("No connection established. An error might have occured.")

# Test the TelnetClient
if __name__ == "__main__":
    client = TelnetClient("localhost", 5000)
    client.connect()
    response = client.send_command("conf t")
    print(response)
    client.close()