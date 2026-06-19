TELEGRAM_MAX_MESSAGE_LENGTH = 4000
TELEGRAM_MAX_BUTTON_TEXT_LENGTH = 64


def truncate_text(text: str, max_length: int) -> str:
  text = text.strip()
  if len(text) <= max_length:
    return text
  if max_length <= 1:
    return text[:max_length]
  return text[: max_length - 1].rstrip() + "…"


def truncate_button_text(text: str) -> str:
  return truncate_text(text, TELEGRAM_MAX_BUTTON_TEXT_LENGTH)


def split_message_parts(
  lines: list[str],
  max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH,
) -> list[str]:
  parts: list[str] = []
  current_lines: list[str] = []
  current_length = 0

  for line in lines:
    line_length = len(line) + (1 if current_lines else 0)
    if current_lines and current_length + line_length > max_length:
      parts.append("\n".join(current_lines))
      current_lines = [line]
      current_length = len(line)
      continue

    current_lines.append(line)
    current_length += line_length

  if current_lines:
    parts.append("\n".join(current_lines))

  return parts
