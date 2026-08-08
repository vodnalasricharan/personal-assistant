from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.settings import Settings


def render_generated_files_page(settings: Settings) -> None:
    st.header("📄 Generated Files")

    generated_dir = settings.generated_dir
    generated_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(generated_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file() and f.name != ".gitkeep"]

    if not files:
        st.info("No generated files yet. Ask the assistant to create a presentation, resume, or document.")
        return

    mime_map = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }

    for file in files:
        col_name, col_size, col_dl, col_del = st.columns([4, 1, 1, 1])
        size_kb = file.stat().st_size / 1024
        col_name.markdown(f"`{file.name}`")
        col_size.caption(f"{size_kb:.1f} KB")
        mime = mime_map.get(file.suffix.lower(), "application/octet-stream")
        with col_dl:
            st.download_button(
                label="⬇️",
                data=file.read_bytes(),
                file_name=file.name,
                mime=mime,
                key=f"dl_{file.name}",
                help="Download file",
            )
        with col_del:
            if st.button("🗑️", key=f"rm_{file.name}", help="Delete file"):
                file.unlink(missing_ok=True)
                st.rerun()
