import re

# Simple keyword based NSFW and abuse detectors (extend as needed)
NSFW_KEYWORDS = ["nsfw", "xxx", "porn", "sex", "adult"]
ABUSE_KEYWORDS = ["fuck", "shit", "idiot", "chutiya", "gandu", "bh*****"]  # add more safely

def contains_nsfw_text(text: str) -> bool:
    if not text:
        return False
    txt = text.lower()
    return any(k in txt for k in NSFW_KEYWORDS)

def contains_abuse(text: str) -> bool:
    if not text:
        return False
    txt = text.lower()
    return any(k in txt for k in ABUSE_KEYWORDS)

def is_nsfw_media(file_name: str = None, caption: str = None) -> bool:
    if caption and contains_nsfw_text(caption):
        return True
    if file_name:
        fn = file_name.lower()
        return any(k in fn for k in NSFW_KEYWORDS)
    return False

