"""Tool approval manager for temporary tool execution approvals.

This module manages temporary approvals for tool executions, allowing users to
approve a tool multiple times without being prompted each time.
"""

from typing import Dict, Optional


class ToolApprovalManager:
    """Manages temporary tool execution approvals with counters.
    
    Users can approve tools individually with a counter. Each approval has a counter
    that decrements with each use until it reaches zero.
    """
    
    def __init__(self):
        """Initialize the tool approval manager."""
        # Per-tool approvals: {"tool_name": remaining_approvals}
        self._tool_approvals: Dict[str, int] = {}
        
        # Per-group approvals: {"tool_group": remaining_approvals}
        # Group names don't include the trailing dot
        self._group_approvals: Dict[str, int] = {}
    
    def _get_tool_group(self, tool_name: str) -> str:
        """Extract the tool group from a tool name.
        
        Args:
            tool_name: Full tool name (e.g., "filesystem.read_file")
            
        Returns:
            Tool group name (e.g., "filesystem")
        """
        if '.' in tool_name:
            return tool_name.split('.', 1)[0]
        return tool_name
    
    def _is_group_tool(self, tool_name: str) -> bool:
        """Check if a tool name represents a tool group (ends with .*)"""
        return tool_name.endswith('.*')
    
    def get_remaining_approvals(self, tool_name: str) -> int:
        """Get the number of remaining approvals for a tool or group.
        
        Args:
            tool_name: Full tool name or group pattern
            
        Returns:
            Number of remaining approvals (0 if not approved or exhausted)
        """
        # Check exact tool approval
        if tool_name in self._tool_approvals:
            return self._tool_approvals[tool_name]
        
        # Check group approval
        if self._is_group_tool(tool_name):
            group = tool_name[:-2]  # Remove trailing .*
            if group in self._group_approvals:
                return self._group_approvals[group]
        
        # Check if this tool belongs to a group
        group = self._get_tool_group(tool_name)
        if group in self._group_approvals:
            return self._group_approvals[group]
        
        return 0
    
    def is_approved(self, tool_name: str) -> bool:
        """Check if a tool is currently approved (has remaining approvals).
        
        Args:
            tool_name: Full tool name
            
        Returns:
            True if tool is approved, False otherwise
        """
        return self.get_remaining_approvals(tool_name) > 0
    
    def decrement_approval(self, tool_name: str) -> None:
        """Decrement the approval counter for a tool.
        
        Args:
            tool_name: Full tool name
        """
        # Try exact tool approval
        if tool_name in self._tool_approvals:
            self._tool_approvals[tool_name] -= 1
            if self._tool_approvals[tool_name] <= 0:
                del self._tool_approvals[tool_name]
            return
        
        # Try group approval
        group = self._get_tool_group(tool_name)
        if group in self._group_approvals:
            self._group_approvals[group] -= 1
            if self._group_approvals[group] <= 0:
                del self._group_approvals[group]
    
    def add_approval(self, tool_name: str, count: int) -> None:
        """Add an approval with the given count.
        
        Args:
            tool_name: Tool name or group pattern (e.g., "filesystem" or "filesystem.*")
            count: Number of approvals to add
        """
        if self._is_group_tool(tool_name):
            group = tool_name[:-2]  # Remove trailing .*
            self._group_approvals[group] = count
        else:
            self._tool_approvals[tool_name] = count
    
    def remove_approval(self, tool_name: str) -> None:
        """Remove an approval for a tool or group.
        
        Args:
            tool_name: Tool name or group pattern
        """
        if tool_name in self._tool_approvals:
            del self._tool_approvals[tool_name]
        
        if self._is_group_tool(tool_name):
            group = tool_name[:-2]
            if group in self._group_approvals:
                del self._group_approvals[group]
    
    def clear_all(self) -> None:
        """Clear all approvals."""
        self._tool_approvals.clear()
        self._group_approvals.clear()
    
    def parse_approval_input(self, input_str: str) -> tuple[str, int]:
        """Parse user input for tool approval.
        
        Supports formats:
        - "10" - approval with counter (old format)
        - "y10" or "Y10" - single tool approval with 'y' prefix
        
        Args:
            input_str: User input (e.g., "10", "y10", "Y10")
            
        Returns:
            Tuple of (tool_name, count) where tool_name is either the tool name
            or a special marker like "Y{count}" for single tools
            
        Raises:
            ValueError: If input is invalid
        """
        input_str = input_str.strip()
        
        if not input_str:
            raise ValueError("Empty input")
        
        # Check for single tool approval with 'y' prefix (y10, Y10 format)
        if input_str[0].upper() == 'Y':
            try:
                count = int(input_str[1:])
                if count <= 0:
                    raise ValueError("Count must be positive")
                return (f"Y{count}", count)  # Special marker for single tool approval
            except ValueError:
                raise ValueError("Invalid count for single tool approval with 'y' prefix")
        
        # Fallback to old format without prefix (just a number like "10")
        try:
            count = int(input_str)
            if count <= 0:
                raise ValueError("Count must be positive")
            return (str(count), count)
        except ValueError:
            raise ValueError("Invalid count - expected format: '10' or 'y10'")
    
    def process_approval_input(self, input_str: str, tool_name: str) -> bool:
        """Process user approval input and update approval state.
        
        Supports formats:
        - "10" or "y10" - single tool approval with counter (old numeric format or y-prefix format)
        
        Args:
            input_str: User input (e.g., "10", "y10", "Y10")
            tool_name: Name of the tool being approved
            
        Returns:
            True if approval was successful, False otherwise
        """
        try:
            parsed_input, count = self.parse_approval_input(input_str)
            
            # Check for y-prefix to determine type
            if parsed_input.startswith('Y'):
                # Single tool approval with y-prefix (y10 or Y10 format)
                self.add_approval(tool_name, count)
            else:
                # Old format without prefix - single tool approval (e.g., "10")
                self.add_approval(tool_name, count)
            
            return True
        except ValueError:
            return False
    
    def get_all_approvals(self) -> dict:
        """Get all current approvals as a dictionary.
        
        Returns:
            Dictionary with tool names/groups and their approval counts
        """
        approvals = {}
        
        for tool, count in self._tool_approvals.items():
            approvals[tool] = count
        
        for group, count in self._group_approvals.items():
            approvals[f"{group}.*"] = count
        
        return approvals
