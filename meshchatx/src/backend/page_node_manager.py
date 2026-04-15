"""PageNodeManager: Manages the lifecycle of multiple PageNode instances.

Handles creation, deletion, persistence, start/stop, and announce
scheduling for page nodes. Each node gets its own subdirectory under
``storage/page_nodes/<node_id>/``.
"""

import os
import uuid

from meshchatx.src.backend.page_node import PageNode


class PageNodeManager:
    """Manages multiple PageNode instances."""

    def __init__(self, storage_dir):
        self.storage_dir = os.path.join(storage_dir, "page_nodes")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.nodes: dict[str, PageNode] = {}

    def load_nodes(self):
        """Discover and load all persisted nodes from disk."""
        if not os.path.isdir(self.storage_dir):
            return

        for entry in os.listdir(self.storage_dir):
            node_dir = os.path.join(self.storage_dir, entry)
            if not os.path.isdir(node_dir):
                continue
            config = PageNode.load_config(node_dir)
            if config is None:
                continue
            node_id = config["node_id"]
            if node_id in self.nodes:
                continue
            node = PageNode(
                node_id=node_id,
                name=config["name"],
                base_dir=node_dir,
            )
            self.nodes[node_id] = node

    def create_node(self, name, node_id=None):
        """Create a new page node, persist its config, and return it."""
        if node_id is None:
            node_id = str(uuid.uuid4())

        node_dir = os.path.join(self.storage_dir, node_id)
        os.makedirs(node_dir, exist_ok=True)

        node = PageNode(node_id=node_id, name=name, base_dir=node_dir)
        node.save_config()
        self.nodes[node_id] = node
        return node

    def delete_node(self, node_id):
        """Stop and remove a node, deleting its directory."""
        node = self.nodes.get(node_id)
        if node is None:
            return False

        if node.running:
            node.teardown()

        import shutil

        shutil.rmtree(node.base_dir, ignore_errors=True)
        del self.nodes[node_id]
        return True

    def start_node(self, node_id):
        """Set up and start serving for a specific node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node {node_id} not found")
        if node.running:
            return node.get_destination_hash()

        dest_hash = node.setup()
        return dest_hash

    def stop_node(self, node_id):
        """Stop serving for a specific node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node {node_id} not found")
        node.teardown()

    def start_all(self):
        """Start all loaded nodes."""
        for node_id in list(self.nodes.keys()):
            try:
                self.start_node(node_id)
            except Exception as e:
                print(f"Failed to start page node {node_id}: {e}")

    def stop_all(self):
        """Stop all running nodes."""
        for node_id in list(self.nodes.keys()):
            try:
                self.stop_node(node_id)
            except Exception as e:
                print(f"Failed to stop page node {node_id}: {e}")

    def announce_node(self, node_id):
        """Send an announce for a specific node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node {node_id} not found")
        node.announce()

    def announce_all(self):
        """Send announces for all running nodes."""
        for node in self.nodes.values():
            if node.running:
                try:
                    node.announce()
                except Exception as e:
                    print(f"Failed to announce page node {node.node_id}: {e}")

    def rename_node(self, node_id, new_name):
        """Rename a node and persist the change."""
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node {node_id} not found")
        node.name = new_name
        node.save_config()

    def get_node(self, node_id):
        """Return a node by id or None."""
        return self.nodes.get(node_id)

    def list_nodes(self):
        """Return status dicts for all nodes."""
        return [node.get_status() for node in self.nodes.values()]

    def teardown(self):
        """Stop all nodes and clear state."""
        self.stop_all()
        self.nodes.clear()
