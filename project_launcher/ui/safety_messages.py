"""Shared user-facing messages for risky file operations."""


def build_delete_confirmation_message(item_type: str, name: str, path: str) -> str:
    """Build a delete confirmation message that clearly states the risk."""
    return (
        f"确定要删除以下{item_type}吗？\n\n"
        f"名称：{name}\n"
        f"路径：{path}\n\n"
        f"此操作会直接从磁盘删除，不会进入回收站。\n"
        f"请确认路径无误。"
    )
