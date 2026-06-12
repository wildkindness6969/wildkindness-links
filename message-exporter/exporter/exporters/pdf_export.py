"""PDF export: one chat-styled PDF per conversation (reportlab Platypus)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
)

from ..models import Conversation, ExportBundle, Message, pretty_handle
from .base import Exporter, ProgressFn, safe_filename

PAGE_MARGIN = 0.75 * inch
BUBBLE_MAX_FRACTION = 0.72
BUBBLE_PAD = 7
BUBBLE_RADIUS = 9
SENT_FILL = colors.HexColor("#1F8FFF")
RECEIVED_FILL = colors.HexColor("#E9E9EB")
META_GREY = colors.HexColor("#8E8E93")
# Bodies longer than this are split into consecutive bubbles so a single
# bubble never exceeds a page.
BUBBLE_SPLIT_CHARS = 3000

_sent_style = ParagraphStyle("sent", fontName="Helvetica", fontSize=10,
                             leading=13, textColor=colors.white)
_received_style = ParagraphStyle("received", fontName="Helvetica", fontSize=10,
                                 leading=13, textColor=colors.black)
_sender_style = ParagraphStyle("sender", fontName="Helvetica", fontSize=7.5,
                               leading=9, textColor=META_GREY)
_day_style = ParagraphStyle("day", fontName="Helvetica-Bold", fontSize=8.5,
                            leading=11, textColor=META_GREY, alignment=TA_CENTER)
_title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16,
                              leading=20)
_subtitle_style = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9.5,
                                 leading=13, textColor=META_GREY)


class ChatBubble(Flowable):
    """A single message bubble: rounded rect, body paragraph, timestamp."""

    TIME_HEIGHT = 10

    def __init__(self, msg: Message, body: str):
        super().__init__()
        self.msg = msg
        style = _sent_style if msg.is_from_me else _received_style
        body_xml = escape(body).replace("\n", "<br/>")
        if msg.attachment_summary and msg.attachment_summary != body:
            grey = "#DDEEFF" if msg.is_from_me else "#8E8E93"
            body_xml += (f'<br/><font size="8" color="{grey}"><i>'
                         f"{escape(msg.attachment_summary)}</i></font>")
        self.para = Paragraph(body_xml, style)
        self.bubble_w = 0.0
        self.bubble_h = 0.0

    def wrap(self, availWidth, availHeight):
        max_text_w = availWidth * BUBBLE_MAX_FRACTION - 2 * BUBBLE_PAD
        w, h = self.para.wrap(max_text_w, availHeight)
        # Shrink the bubble to the longest rendered line.
        used = max((line_w for line_w in self._line_widths()), default=w)
        self.bubble_w = min(max_text_w, max(used, 18)) + 2 * BUBBLE_PAD
        self.bubble_h = h + 2 * BUBBLE_PAD
        self.width = availWidth
        self.height = self.bubble_h + self.TIME_HEIGHT
        return self.width, self.height

    def _line_widths(self):
        try:
            for line in self.para.blPara.lines:
                if isinstance(line, tuple):   # simple-paragraph form
                    yield self.para.width - line[0]
                else:
                    yield self.para.width - getattr(line, "extraSpace", 0)
        except Exception:
            return

    def draw(self):
        c = self.canv
        from_me = self.msg.is_from_me
        x = self.width - self.bubble_w if from_me else 0
        y = self.TIME_HEIGHT
        c.saveState()
        c.setFillColor(SENT_FILL if from_me else RECEIVED_FILL)
        c.setStrokeColor(SENT_FILL if from_me else RECEIVED_FILL)
        c.roundRect(x, y, self.bubble_w, self.bubble_h, BUBBLE_RADIUS,
                    stroke=0, fill=1)
        self.para.drawOn(c, x + BUBBLE_PAD, y + BUBBLE_PAD)
        c.setFillColor(META_GREY)
        c.setFont("Helvetica", 7)
        stamp = self.msg.timestamp.strftime(_TIME_FMT)
        if from_me:
            c.drawRightString(self.width, 1, stamp)
        else:
            c.drawString(0, 1, stamp)
        c.restoreState()


class DaySeparator(Flowable):
    """Centered date label with hairline rules on each side."""

    def __init__(self, day: date):
        super().__init__()
        self.label = day.strftime(_DAY_FMT)
        self.height = 18

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(META_GREY)
        text_w = c.stringWidth(self.label, "Helvetica-Bold", 8.5)
        mid_y = self.height / 2 - 3
        c.drawCentredString(self.width / 2, mid_y, self.label)
        c.setStrokeColor(colors.HexColor("#D9D9DE"))
        c.setLineWidth(0.5)
        gap = text_w / 2 + 10
        c.line(0, mid_y + 3, self.width / 2 - gap, mid_y + 3)
        c.line(self.width / 2 + gap, mid_y + 3, self.width, mid_y + 3)
        c.restoreState()


def _supports_dash_fmt() -> bool:
    # "%-d" (no zero padding) is glibc/macOS only; Windows uses "%#d".
    try:
        return bool(date(2000, 1, 2).strftime("%-d"))
    except ValueError:
        return False


if _supports_dash_fmt():
    _TIME_FMT, _DAY_FMT = "%-I:%M %p", "%A, %B %-d, %Y"
else:
    _TIME_FMT, _DAY_FMT = "%I:%M %p", "%A, %B %d, %Y"


class PdfExporter(Exporter):
    name = "pdf"

    def export(self, bundle: ExportBundle, out_dir: Path,
               progress: ProgressFn | None = None) -> list[Path]:
        pdf_dir = Path(out_dir) / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        total = len(bundle.conversations) or 1
        for i, convo in enumerate(bundle.conversations):
            if progress:
                progress(f"PDF: {convo.display_name} "
                         f"({i + 1} of {total})", i / total)
            filename = f"{safe_filename(convo.display_name)}-{convo.chat_rowid}.pdf"
            path = pdf_dir / filename
            self._build_pdf(convo, bundle, path)
            outputs.append(path)
        return outputs

    def _build_pdf(self, convo: Conversation, bundle: ExportBundle,
                   path: Path) -> None:
        doc = SimpleDocTemplate(
            str(path), pagesize=letter,
            leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
            topMargin=PAGE_MARGIN + 12, bottomMargin=PAGE_MARGIN,
            title=f"Messages — {convo.display_name}",
        )
        story: list[Flowable] = list(self._cover_block(convo, bundle))
        last_day: date | None = None
        last_sender: str | None = None
        for msg in convo.messages:
            day = msg.timestamp.date()
            if day != last_day:
                story.append(Spacer(1, 6))
                story.append(DaySeparator(day))
                story.append(Spacer(1, 4))
                last_day = day
                last_sender = None
            show_sender = (convo.is_group and not msg.is_from_me
                           and msg.sender_handle != last_sender)
            last_sender = msg.sender_handle if not msg.is_from_me else None
            for chunk in _split_body(msg.text):
                bubble = ChatBubble(msg, chunk)
                if show_sender:
                    label = Paragraph(escape(msg.sender_name), _sender_style)
                    story.append(KeepTogether([label, bubble]))
                    show_sender = False
                else:
                    story.append(bubble)
                story.append(Spacer(1, 3))

        header = _HeaderFooter(convo.display_name, bundle)
        doc.build(story, onFirstPage=header, onLaterPages=header)

    def _cover_block(self, convo: Conversation, bundle: ExportBundle):
        yield Paragraph(escape(convo.display_name), _title_style)
        participants = ", ".join(
            f"{p.display} ({pretty_handle(p.handle)})" if p.name else p.display
            for p in convo.participants) or "Unknown"
        first = convo.first_timestamp.strftime("%b %d, %Y") \
            if convo.first_timestamp else "—"
        last = convo.last_timestamp.strftime("%b %d, %Y") \
            if convo.last_timestamp else "—"
        yield Paragraph(
            f"With: {escape(participants)}<br/>"
            f"{len(convo.messages):,} messages · {first} – {last}",
            _subtitle_style)
        yield Spacer(1, 10)


class _HeaderFooter:
    def __init__(self, convo_name: str, bundle: ExportBundle):
        self.convo_name = convo_name
        self.right = (f"Exported {bundle.export_date.strftime('%Y-%m-%d')} · "
                      f"{pretty_handle(bundle.owner_number)}")

    def __call__(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(META_GREY)
        top = letter[1] - PAGE_MARGIN + 4
        name = self.convo_name
        if len(name) > 60:
            name = name[:57] + "…"
        canvas.drawString(PAGE_MARGIN, top, name)
        canvas.drawRightString(letter[0] - PAGE_MARGIN, top, self.right)
        canvas.drawCentredString(letter[0] / 2, PAGE_MARGIN / 2,
                                 f"Page {doc.page}")
        canvas.restoreState()


def _split_body(text: str) -> list[str]:
    if len(text) <= BUBBLE_SPLIT_CHARS:
        return [text]
    chunks = []
    while text:
        cut = text.rfind(" ", 0, BUBBLE_SPLIT_CHARS) if len(text) > BUBBLE_SPLIT_CHARS \
            else len(text)
        if cut <= 0:
            cut = min(BUBBLE_SPLIT_CHARS, len(text))
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    return chunks
