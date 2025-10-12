"""Enhanced file system operations agent with full CRUD capabilities."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from rich.console import Console
import ollama
from contextlib import AsyncExitStack
import os
import shutil
import json

from .base import SubAgent
from .communication import MessageBroker


class FileSystemAgent(SubAgent):
    """Specialized agent for file system operations.
    
    This agent provides comprehensive file and directory management:
    - Read files and directories
    - Write and create new files
    - Edit and modify existing files
    - Delete files and directories
    - Move and copy operations
    - Search and find files
    - File metadata and permissions
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert file system management agent.

Your responsibilities include:
1. Reading and analyzing file contents
2. Creating and writing new files
3. Editing and modifying existing files
4. Deleting files and directories safely
5. Moving and copying files
6. Searching for files and patterns
7. Managing file permissions and metadata
8. Organizing directory structures

When working with files:
- Always verify file existence before operations
- Use absolute paths for clarity
- Handle errors gracefully
- Preserve important data with backups when modifying
- Respect file permissions and security
- Provide clear feedback on operations
- Use appropriate encoding (UTF-8 by default)
- Handle binary and text files appropriately

Available operations:
- read_file(path): Read file contents
- write_file(path, content): Write content to file
- edit_file(path, search, replace): Find and replace in file
- delete_file(path): Delete a file
- delete_directory(path): Delete a directory
- create_directory(path): Create directory
- list_directory(path): List directory contents
- move_file(src, dst): Move/rename file
- copy_file(src, dst): Copy file
- search_files(pattern, directory): Search for files
- get_file_info(path): Get file metadata

Always confirm operations and provide status feedback.
"""
    
    def __init__(
        self,
        name: str = "filesystem",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize FileSystem agent."""
        description = "Specialized agent for file system operations (read, write, edit, delete)"
        system_prompt = custom_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        super().__init__(
            name=name,
            description=description,
            model=model,
            system_prompt=system_prompt,
            console=console,
            ollama_client=ollama_client,
            parent_exit_stack=parent_exit_stack,
            message_broker=message_broker,
            enable_memory=True
        )
        
        self.operations_log: List[Dict[str, Any]] = []
    
    async def read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read contents of a file.
        
        Args:
            file_path: Path to file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            str: File contents
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            if not path.is_file():
                return f"Error: Not a file: {file_path}"
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            self.operations_log.append({
                "operation": "read",
                "path": str(path),
                "success": True
            })
            
            await self.remember(
                f"Read file: {file_path}",
                importance=2,
                tags=["filesystem", "read"]
            )
            
            return content
            
        except Exception as e:
            error_msg = f"Error reading file {file_path}: {str(e)}"
            self.operations_log.append({
                "operation": "read",
                "path": file_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> str:
        """Write content to a file.
        
        Args:
            file_path: Path to file to write
            content: Content to write
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist
            
        Returns:
            str: Success or error message
        """
        try:
            path = Path(file_path).resolve()
            
            # Create parent directories if needed
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            self.operations_log.append({
                "operation": "write",
                "path": str(path),
                "success": True,
                "size": len(content)
            })
            
            await self.remember(
                f"Wrote file: {file_path} ({len(content)} chars)",
                importance=3,
                tags=["filesystem", "write"]
            )
            
            return f"Successfully wrote {len(content)} characters to {file_path}"
            
        except Exception as e:
            error_msg = f"Error writing file {file_path}: {str(e)}"
            self.operations_log.append({
                "operation": "write",
                "path": file_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def edit_file(
        self,
        file_path: str,
        search_text: str,
        replace_text: str,
        encoding: str = "utf-8"
    ) -> str:
        """Edit a file by finding and replacing text.
        
        Args:
            file_path: Path to file to edit
            search_text: Text to search for
            replace_text: Text to replace with
            encoding: File encoding (default: utf-8)
            
        Returns:
            str: Success or error message
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            # Read current content
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Check if search text exists
            if search_text not in content:
                return f"Error: Search text not found in {file_path}"
            
            # Count occurrences
            count = content.count(search_text)
            
            # Perform replacement
            new_content = content.replace(search_text, replace_text)
            
            # Write back
            with open(path, 'w', encoding=encoding) as f:
                f.write(new_content)
            
            self.operations_log.append({
                "operation": "edit",
                "path": str(path),
                "success": True,
                "replacements": count
            })
            
            await self.remember(
                f"Edited file: {file_path} ({count} replacements)",
                importance=3,
                tags=["filesystem", "edit"]
            )
            
            return f"Successfully replaced {count} occurrence(s) in {file_path}"
            
        except Exception as e:
            error_msg = f"Error editing file {file_path}: {str(e)}"
            self.operations_log.append({
                "operation": "edit",
                "path": file_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def delete_file(self, file_path: str) -> str:
        """Delete a file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            str: Success or error message
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            if not path.is_file():
                return f"Error: Not a file: {file_path}"
            
            # Get file info before deletion
            file_size = path.stat().st_size
            
            path.unlink()
            
            self.operations_log.append({
                "operation": "delete",
                "path": str(path),
                "success": True,
                "size": file_size
            })
            
            await self.remember(
                f"Deleted file: {file_path}",
                importance=4,
                tags=["filesystem", "delete"]
            )
            
            return f"Successfully deleted {file_path}"
            
        except Exception as e:
            error_msg = f"Error deleting file {file_path}: {str(e)}"
            self.operations_log.append({
                "operation": "delete",
                "path": file_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def delete_directory(self, dir_path: str, recursive: bool = False) -> str:
        """Delete a directory.
        
        Args:
            dir_path: Path to directory to delete
            recursive: Delete recursively if directory is not empty
            
        Returns:
            str: Success or error message
        """
        try:
            path = Path(dir_path).resolve()
            
            if not path.exists():
                return f"Error: Directory not found: {dir_path}"
            
            if not path.is_dir():
                return f"Error: Not a directory: {dir_path}"
            
            if recursive:
                shutil.rmtree(path)
                msg = f"Successfully deleted directory (recursive): {dir_path}"
            else:
                path.rmdir()
                msg = f"Successfully deleted directory: {dir_path}"
            
            self.operations_log.append({
                "operation": "delete_directory",
                "path": str(path),
                "success": True,
                "recursive": recursive
            })
            
            await self.remember(
                f"Deleted directory: {dir_path} (recursive={recursive})",
                importance=4,
                tags=["filesystem", "delete"]
            )
            
            return msg
            
        except Exception as e:
            error_msg = f"Error deleting directory {dir_path}: {str(e)}"
            self.operations_log.append({
                "operation": "delete_directory",
                "path": dir_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def create_directory(self, dir_path: str, parents: bool = True) -> str:
        """Create a directory.
        
        Args:
            dir_path: Path to directory to create
            parents: Create parent directories if they don't exist
            
        Returns:
            str: Success or error message
        """
        try:
            path = Path(dir_path).resolve()
            
            if path.exists():
                return f"Directory already exists: {dir_path}"
            
            path.mkdir(parents=parents, exist_ok=False)
            
            self.operations_log.append({
                "operation": "create_directory",
                "path": str(path),
                "success": True
            })
            
            await self.remember(
                f"Created directory: {dir_path}",
                importance=2,
                tags=["filesystem", "create"]
            )
            
            return f"Successfully created directory: {dir_path}"
            
        except Exception as e:
            error_msg = f"Error creating directory {dir_path}: {str(e)}"
            self.operations_log.append({
                "operation": "create_directory",
                "path": dir_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def list_directory(self, dir_path: str = ".", pattern: str = "*") -> str:
        """List contents of a directory.
        
        Args:
            dir_path: Path to directory to list
            pattern: Glob pattern to filter files
            
        Returns:
            str: Formatted directory listing
        """
        try:
            path = Path(dir_path).resolve()
            
            if not path.exists():
                return f"Error: Directory not found: {dir_path}"
            
            if not path.is_dir():
                return f"Error: Not a directory: {dir_path}"
            
            items = sorted(path.glob(pattern))
            
            result = [f"Contents of {dir_path}:"]
            result.append(f"{'Type':<10} {'Size':<12} {'Name'}")
            result.append("-" * 60)
            
            for item in items:
                item_type = "DIR" if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else "-"
                size_str = f"{size:,}" if isinstance(size, int) else size
                result.append(f"{item_type:<10} {size_str:<12} {item.name}")
            
            result.append(f"\nTotal: {len(items)} items")
            
            self.operations_log.append({
                "operation": "list",
                "path": str(path),
                "success": True,
                "items": len(items)
            })
            
            return "\n".join(result)
            
        except Exception as e:
            error_msg = f"Error listing directory {dir_path}: {str(e)}"
            self.operations_log.append({
                "operation": "list",
                "path": dir_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def move_file(self, src_path: str, dst_path: str) -> str:
        """Move or rename a file.
        
        Args:
            src_path: Source file path
            dst_path: Destination file path
            
        Returns:
            str: Success or error message
        """
        try:
            src = Path(src_path).resolve()
            dst = Path(dst_path).resolve()
            
            if not src.exists():
                return f"Error: Source file not found: {src_path}"
            
            if dst.exists():
                return f"Error: Destination already exists: {dst_path}"
            
            # Create destination directory if needed
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src), str(dst))
            
            self.operations_log.append({
                "operation": "move",
                "src": str(src),
                "dst": str(dst),
                "success": True
            })
            
            await self.remember(
                f"Moved file: {src_path} → {dst_path}",
                importance=3,
                tags=["filesystem", "move"]
            )
            
            return f"Successfully moved {src_path} to {dst_path}"
            
        except Exception as e:
            error_msg = f"Error moving file: {str(e)}"
            self.operations_log.append({
                "operation": "move",
                "src": src_path,
                "dst": dst_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def copy_file(self, src_path: str, dst_path: str) -> str:
        """Copy a file.
        
        Args:
            src_path: Source file path
            dst_path: Destination file path
            
        Returns:
            str: Success or error message
        """
        try:
            src = Path(src_path).resolve()
            dst = Path(dst_path).resolve()
            
            if not src.exists():
                return f"Error: Source file not found: {src_path}"
            
            if not src.is_file():
                return f"Error: Source is not a file: {src_path}"
            
            # Create destination directory if needed
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(str(src), str(dst))
            
            self.operations_log.append({
                "operation": "copy",
                "src": str(src),
                "dst": str(dst),
                "success": True
            })
            
            await self.remember(
                f"Copied file: {src_path} → {dst_path}",
                importance=2,
                tags=["filesystem", "copy"]
            )
            
            return f"Successfully copied {src_path} to {dst_path}"
            
        except Exception as e:
            error_msg = f"Error copying file: {str(e)}"
            self.operations_log.append({
                "operation": "copy",
                "src": src_path,
                "dst": dst_path,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def search_files(
        self,
        directory: str,
        pattern: str,
        content_search: Optional[str] = None
    ) -> str:
        """Search for files in a directory.
        
        Args:
            directory: Directory to search in
            pattern: File name pattern (glob)
            content_search: Optional text to search within files
            
        Returns:
            str: Search results
        """
        try:
            path = Path(directory).resolve()
            
            if not path.exists():
                return f"Error: Directory not found: {directory}"
            
            # Find files matching pattern
            matches = list(path.rglob(pattern))
            
            result = [f"Search results in {directory} for pattern '{pattern}':"]
            
            if content_search:
                # Search file contents
                content_matches = []
                for file_path in matches:
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if content_search in content:
                                    count = content.count(content_search)
                                    content_matches.append((file_path, count))
                        except:
                            pass
                
                result.append(f"\nFiles containing '{content_search}':")
                for file_path, count in content_matches:
                    rel_path = file_path.relative_to(path)
                    result.append(f"  {rel_path} ({count} occurrence(s))")
                
                result.append(f"\nTotal: {len(content_matches)} files with matches")
            else:
                # Just list matching files
                for file_path in matches:
                    rel_path = file_path.relative_to(path)
                    file_type = "DIR" if file_path.is_dir() else "FILE"
                    result.append(f"  [{file_type}] {rel_path}")
                
                result.append(f"\nTotal: {len(matches)} matches")
            
            self.operations_log.append({
                "operation": "search",
                "path": str(path),
                "pattern": pattern,
                "success": True,
                "matches": len(matches)
            })
            
            return "\n".join(result)
            
        except Exception as e:
            error_msg = f"Error searching files: {str(e)}"
            self.operations_log.append({
                "operation": "search",
                "path": directory,
                "success": False,
                "error": str(e)
            })
            return error_msg
    
    async def get_file_info(self, file_path: str) -> str:
        """Get metadata about a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            str: Formatted file information
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            stat = path.stat()
            
            info = {
                "Path": str(path),
                "Name": path.name,
                "Type": "Directory" if path.is_dir() else "File",
                "Size": f"{stat.st_size:,} bytes",
                "Modified": stat.st_mtime,
                "Created": stat.st_ctime,
                "Permissions": oct(stat.st_mode)[-3:],
            }
            
            result = [f"Information for {file_path}:"]
            for key, value in info.items():
                result.append(f"  {key}: {value}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"Error getting file info: {str(e)}"
    
    def get_operations_summary(self) -> Dict[str, Any]:
        """Get summary of file operations performed.
        
        Returns:
            Dict with operation statistics
        """
        summary = {
            "total_operations": len(self.operations_log),
            "successful": len([op for op in self.operations_log if op["success"]]),
            "failed": len([op for op in self.operations_log if not op["success"]]),
            "by_type": {}
        }
        
        for op in self.operations_log:
            op_type = op["operation"]
            if op_type not in summary["by_type"]:
                summary["by_type"][op_type] = {"total": 0, "success": 0, "failed": 0}
            
            summary["by_type"][op_type]["total"] += 1
            if op["success"]:
                summary["by_type"][op_type]["success"] += 1
            else:
                summary["by_type"][op_type]["failed"] += 1
        
        return summary
