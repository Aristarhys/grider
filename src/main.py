import logging
import os

from typing import List, Optional, Tuple
from collections import Counter
from tempfile import NamedTemporaryFile

import gradio as gr
from PIL import Image, ImageColor

from grider.constants import DEFAULT_OUTPUT_TYPE, MODE_BY_OUTPUT_TYPE, OUTPUT_TYPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_grid_image(
    images: List[NamedTemporaryFile],
    bg_color: str,
    columns: int,
    padding: int,
    output_type: str,
    progress=gr.Progress(),
) -> str:
    if not images:
        raise gr.Error("Upload some images first!")
    images_count: int = len(images)
    if images_count == 1:
        raise gr.Error("Select multiple images!") 
    padding_col: int = padding
    padding_row: int = padding
    rows: int = int(images_count / columns) or 1 
    pos_x: int = padding_col
    pos_y: int = padding_row
    _images: List[Image] = []
    image_sizes: List[Tuple[int, int]] = []
    for image in images:
        _image: Image = Image.open(image.name)
        image_sizes.append(_image.size)
        _images.append(_image)
    tile_size = Counter(image_sizes).most_common(1)[0][0]
    tile_width, tile_height = tile_size
    logger.info("Most common image size is %d x %d", tile_width, tile_height)
    output_width: int = columns * (tile_width + padding_col) + padding_col
    output_height: int = rows * (tile_height + padding_row) + padding_row
    output_mode = MODE_BY_OUTPUT_TYPE[output_type]
    output_image: Image = Image.new(output_mode, (output_width, output_height), ImageColor.getrgb(bg_color))
    is_multi_column = columns > 1
    for index, image in enumerate(progress.tqdm(_images, unit="images", total=images_count)):
        if image.size == tile_size:
            tile = image
        else:
            logger.warning("Resizing image %d to match most common size", index)
            tile = image.resize(tile_size, Image.Resampling.LANCZOS)
        output_image.paste(tile, (pos_x, pos_y))
        if is_multi_column:
            pos_x += tile_width + padding_col
        if (index and index % columns == 0) or not is_multi_column:
            pos_x = padding_col
            pos_y += tile_height + padding_row
    with NamedTemporaryFile() as tf:
        output_file_path = tf.name
    output_file_extension = output_type.lower()
    output_image_path = f"{output_file_path}.{output_file_extension}"
    logger.info("Saving output image to %s", output_image_path)
    output_image.save(output_image_path, output_type)        
    return output_image_path


if __name__ == "__main__":
    images_picker = gr.File(file_count="multiple", file_types=["image"])
    bg_color = gr.ColorPicker(label="Background color")
    columns_count = gr.Number(label="Columns count", minimum=1, value=4, precision=0)
    tile_padding = gr.Number(label="Tile padding", minimum=0, value=5, precision=0)
    output_type = gr.Dropdown(OUTPUT_TYPES, label="Output image type", value=DEFAULT_OUTPUT_TYPE)
    output = gr.Image(type="filepath", label="Grid Image")
    grider = gr.Interface(
        fn=make_grid_image,
        inputs=[images_picker, bg_color, columns_count, tile_padding, output_type],
        outputs=[output],
        allow_flagging="never",
        title="Grider",
    )
    grider.queue()
    logger.info("Starting grider")
    grider.launch()
