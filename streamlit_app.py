mport streamlit as st
import cv2
import numpy as np
import tempfile
from pathlib import Path
from renderer import Options, render_text, save_pdf
from extract_glyphs import extract_from_images

st.set_page_config(page_title="My Handwriting Generator", page_icon="✍️")
st.title("✍️ My Handwriting Generator")
st.write("Convert your text into a PDF using your own handwriting.")

uploaded = st.file_uploader(
"Upload your completed handwriting template",
type=["png", "jpg", "jpeg"]
)

text = st.text_area("Enter your text", height=200)

if st.button("Generate PDF"):
if uploaded is None:
st.error("Please upload your handwriting template.")
elif not text.strip():
st.error("Please enter some text.")
else:
image_data = np.frombuffer(uploaded.getvalue(), dtype=np.uint8)
image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    if image is None:
        st.error("Invalid image. Please upload a clear JPG or PNG.")
    else:
        with st.spinner("Generating your PDF..."):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    glyph_dir = Path(tmp) / "glyphs"
                    missing, _ = extract_from_images([image], glyph_dir)

                    pages, unsupported = render_text(
                        text, glyph_dir, Options()
                    )

                    pdf_path = Path(tmp) / "handwriting.pdf"
                    save_pdf(pages, str(pdf_path))
                    pdf_bytes = pdf_path.read_bytes()

                if missing:
                    st.warning(
                        "Missing characters on your template: "
                        + "".join(missing)
                    )

                if unsupported:
                    st.warning(
                        "Unsupported characters: "
                        + "".join(sorted(unsupported))
                    )

                st.success("Your PDF is ready!")
                st.download_button(
                    "Download your handwriting PDF",
                    data=pdf_bytes,
                    file_name="handwriting.pdf",
                    mime="application/pdf"
                )

            except Exception as error:
                st.error(f"Generation failed: {error}")
