from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


def validate_image_upload(upload, *, max_size):
    if upload.size > max_size:
        raise ValueError(f"Image must be at most {max_size // 1024 // 1024} MB.")
    try:
        image = Image.open(upload)
        image.verify()
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValueError("Upload must be a JPEG, PNG, WEBP, or GIF image.")
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("Upload must be a valid image file.")
    finally:
        upload.seek(0)
