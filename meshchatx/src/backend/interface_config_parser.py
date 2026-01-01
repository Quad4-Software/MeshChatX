import RNS.vendor.configobj


class InterfaceConfigParser:
    @staticmethod
    def parse(text):
        # get lines from provided text
        lines = text.splitlines()
        stripped_lines = [line.strip() for line in lines]

        # ensure [interfaces] section exists
        if "[interfaces]" not in stripped_lines:
            lines.insert(0, "[interfaces]")
            stripped_lines.insert(0, "[interfaces]")

        try:
            # parse lines as rns config object
            config = RNS.vendor.configobj.ConfigObj(lines)
        except Exception as e:
            print(f"Failed to parse interface config with ConfigObj: {e}")
            return InterfaceConfigParser._parse_best_effort(lines)

        # get interfaces from config
        config_interfaces = config.get("interfaces", {})
        if config_interfaces is None:
            return []

        # process interfaces
        interfaces = []
        for interface_name in config_interfaces:
            # ensure interface has a name
            interface_config = config_interfaces[interface_name]
            interface_config["name"] = interface_name
            interfaces.append(interface_config)

        return interfaces

    @staticmethod
    def _parse_best_effort(lines):
        interfaces = []
        current_interface_name = None
        current_interface = {}
        current_sub_name = None
        current_sub = None

        def commit_sub():
            nonlocal current_sub_name, current_sub
            if current_sub_name and current_sub is not None:
                current_interface[current_sub_name] = current_sub
            current_sub_name = None
            current_sub = None

        def commit_interface():
            nonlocal current_interface_name, current_interface
            if current_interface_name:
                # shallow copy to avoid future mutation
                interfaces.append(dict(current_interface))
            current_interface_name = None
            current_interface = {}

        for raw_line in lines:
            line = raw_line.strip()
            if line == "" or line.startswith("#"):
                continue

            if line.lower() == "[interfaces]":
                continue

            if line.startswith("[[[") and line.endswith("]]]"):
                commit_sub()
                current_sub_name = line[3:-3].strip()
                current_sub = {}
                continue

            if line.startswith("[[") and line.endswith("]]"):
                commit_sub()
                commit_interface()
                current_interface_name = line[2:-2].strip()
                current_interface = {"name": current_interface_name}
                continue

            if "=" in line and current_interface_name is not None:
                key, value = line.split("=", 1)
                target = current_sub if current_sub is not None else current_interface
                target[key.strip()] = value.strip()

        # commit any pending sections
        commit_sub()
        commit_interface()

        return interfaces
