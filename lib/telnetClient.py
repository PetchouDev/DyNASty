import telnetlib
from threading import Thread
import time
import sys
from tkinter import Frame  # pour éviter l'erreur dans MessageBox si utilisé

def clear_lines(n):
        for _ in range(n):
            sys.stdout.write('\x1b[1A')  # Move cursor up
            sys.stdout.write('\x1b[2K')  # Clear entire line

class TelnetClient:
    def __init__(self, host, port=23, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connection = None
        self.done = False

    def connect(self):
        try:
            self.connection = telnetlib.Telnet(self.host, self.port, self.timeout)
            # print(f"Connected to {self.host}:{self.port}")
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
                # print(f"Failed to send command '{command}' - {e}")
                return None
        else:
            print("No connection established.")
            return None

    def close(self):
        if self.connection:
            self.connection.close()
            #print("Connection closed.")

    def push_configuration(self, config_commands: str):
        self.done = False
        if not self.connection:
            self.connect()
        if self.connection:
            try:
                self.send_command("")
                self.send_command("")
                for command in config_commands.splitlines():
                    self.send_command(command.strip())
                    self.send_command("")
            except Exception as e:
                #print(f"Failed to push configuration - {e}")
                pass
            finally:
                self.done = True
                self.close()
        else:
            self.done = True
            print("No connection established. An error might have occurred.")


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.loading_states = "⣾⣽⣻⢿⡿⣟⣯⣷"
        self.loader_index = 0
        self.threads = []
        self.has_printed = 0

    def push_configuration(self, name, host, port, config_commands):
        client = TelnetClient(host, port)
        self.sessions[name] = client
        thread = Thread(target=client.push_configuration, args=(config_commands,))
        self.threads.append(thread)
        thread.start()

    def all_done(self):
        return all(session.done for session in self.sessions.values())
    
    def terminate_all(self):
        """Forcefully terminate all sessions."""
        for session in self.sessions.values():
            if session.connection:
                session.connection.close()
        self.sessions.clear()
        self.threads.clear()

    def status(self, flush=False):
        if flush and self.has_printed > 0:
            clear_lines(self.has_printed)
            self.has_printed = 0

        self.loader_index = (self.loader_index + 1) % len(self.loading_states)
        loading_state = self.loading_states[self.loader_index]

        lines = []
        done = 0
        for name, session in self.sessions.items():
            short_name = name.split(".")[0]  # Juste le nom court ou IP partielle
            if session.done:
                done += 1
                lines.append(f"{short_name:<8} \033[92m✓ pushed\033[0m")
            else:
                lines.append(f"{short_name:<8} \033[94m{loading_state} pushing...\033[0m")

        lines = "\n".join(lines)
        print(f"{lines}\n{done}/{len(self.sessions)} nodes completed.")
        self.has_printed = len(lines) + 2

    def wait_all(self):
        for t in self.threads:
            t.join()
