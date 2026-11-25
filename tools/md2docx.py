# -*- coding: utf-8 -*-
"""把项目里的 Markdown 资料汇编转成排版良好的 DOCX。"""
import re
import sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml
from docx.opc.constants import RELATIONSHIP_TYPE as RT

BODY_EA = "微软雅黑"
BODY_LATIN = "Segoe UI"
CODE_FONT = "Consolas"

INLINE_RE = re.compile(
    r"\[([^\]]+)\]\(([^)\s]+)\)"      # 1,2 link
    r"|\*\*([^*]+)\*\*"                # 3 bold
    r"|`([^`]+)`"                      # 4 code
)


def set_run_font(run, latin=BODY_LATIN, ea=BODY_EA, size=None, bold=None, color=None):
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), ea)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def shade_run(run, fill="F2F2F2"):
    rpr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rpr.append(shd)


def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def add_hyperlink(paragraph, url, text, size=None):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), BODY_LATIN)
    rFonts.set(qn("w:hAnsi"), BODY_LATIN)
    rFonts.set(qn("w:eastAsia"), BODY_EA)
    rPr.append(rFonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1155CC")
    rPr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        rPr.append(sz)
        szcs = OxmlElement("w:szCs")
        szcs.set(qn("w:val"), str(int(size * 2)))
        rPr.append(szcs)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_inline(paragraph, text, size=10.5, base_bold=False, color=None):
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            r = paragraph.add_run(text[pos:m.start()])
            set_run_font(r, size=size, bold=base_bold, color=color)
        if m.group(1) is not None:
            add_hyperlink(paragraph, m.group(2), m.group(1), size=size)
        elif m.group(3) is not None:
            r = paragraph.add_run(m.group(3))
            set_run_font(r, size=size, bold=True, color=color)
        else:
            r = paragraph.add_run(m.group(4))
            set_run_font(r, latin=CODE_FONT, ea=CODE_FONT, size=size - 0.5, color="9C2A00")
            shade_run(r)
        pos = m.end()
    if pos < len(text):
        r = paragraph.add_run(text[pos:])
        set_run_font(r, size=size, bold=base_bold, color=color)


def add_page_number_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("— ")
    set_run_font(run, size=8.5, color="808080")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)
    run2 = p.add_run(" —")
    set_run_font(run2, size=8.5, color="808080")


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def prevent_row_split(row):
    trPr = row._tr.get_or_add_trPr()
    cantSplit = OxmlElement("w:cantSplit")
    trPr.append(cantSplit)


COL_WIDTHS = {
    2: [32, 68],
    3: [20, 34, 46],
    4: [14, 26, 28, 32],
    5: [12, 22, 22, 22, 22],
}


def build(md_path, out_path):
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)

    def set_style_ea(style, ea=BODY_EA):
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:eastAsia"), ea)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_LATIN
    normal.font.size = Pt(10.5)
    set_style_ea(normal)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.25

    for name, size, color in (("Heading 1", 16, "1F3864"), ("Heading 2", 13, "2E5496"), ("Heading 3", 11.5, "2E5496")):
        st = doc.styles[name]
        st.font.name = BODY_LATIN
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor.from_string(color)
        set_style_ea(st)
        st.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 9)
        st.paragraph_format.space_after = Pt(4)
        st.paragraph_format.keep_with_next = True

    add_page_number_footer(sec)

    i = 0
    n = len(lines)
    total_w = 16.6
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 代码块
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.4)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "F5F5F5")
            pPr.append(shd)
            r = p.add_run("\n".join(buf))
            maxlen = max((len(x) for x in buf), default=0)
            code_size = 8.5 if maxlen <= 88 else (8.0 if maxlen <= 96 else 7.4)
            set_run_font(r, latin=CODE_FONT, ea=CODE_FONT, size=code_size)
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            ncols = len(header)
            table = doc.add_table(rows=1, cols=ncols)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            widths = COL_WIDTHS.get(ncols, [total_w / ncols] * ncols)
            if ncols == 3 and header[0] == "类别" and header[2] == "体积":
                widths = [18, 58, 24]
            hdr = table.rows[0]
            repeat_header(hdr)
            for j, cell_text in enumerate(header):
                cell = hdr.cells[j]
                cell.width = Cm(total_w * widths[j] / 100)
                shade_cell(cell, "DCE6F1")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(1)
                add_inline(p, cell_text, size=9, base_bold=True, color="1F3864")
            for row_data in rows:
                row = table.add_row()
                prevent_row_split(row)
                for j in range(ncols):
                    cell = row.cells[j]
                    cell.width = Cm(total_w * widths[j] / 100)
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(1)
                    txt = row_data[j] if j < len(row_data) else ""
                    add_inline(p, txt, size=9)
            # 表后留白
            after = doc.add_paragraph()
            after.paragraph_format.space_after = Pt(2)
            r = after.add_run("")
            set_run_font(r, size=4)
            continue

        # 标题
        if stripped.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(10)
            add_inline(p, stripped[2:], size=20, base_bold=True, color="1F3864")
            i += 1
            continue
        if stripped.startswith("## "):
            p = doc.add_paragraph(style="Heading 1")
            add_inline(p, stripped[3:], size=15, base_bold=True, color="1F3864")
            i += 1
            continue
        if stripped.startswith("### "):
            p = doc.add_paragraph(style="Heading 2")
            add_inline(p, stripped[4:], size=12.5, base_bold=True, color="2E5496")
            i += 1
            continue

        # 分隔线
        if stripped == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            pPr = p._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "BFBFBF")
            pbdr.append(bottom)
            pPr.append(pbdr)
            i += 1
            continue

        # 引用
        if stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            left = OxmlElement("w:left")
            left.set(qn("w:val"), "single")
            left.set(qn("w:sz"), "18")
            left.set(qn("w:space"), "8")
            left.set(qn("w:color"), "8EAADB")
            pbdr.append(left)
            pPr.append(pbdr)
            add_inline(p, stripped[2:], size=9.5, color="404040")
            i += 1
            continue

        # 列表
        if re.match(r"^[-*] ", stripped):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(0.75)
            add_inline(p, stripped[2:], size=10.5)
            i += 1
            continue
        if re.match(r"^\d+\. ", stripped):
            m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.95)
            p.paragraph_format.first_line_indent = Cm(-0.55)
            p.paragraph_format.space_after = Pt(2)
            num = p.add_run(m.group(1) + ".\t")
            set_run_font(num, size=10.5, bold=True, color="1F3864")
            add_inline(p, m.group(2), size=10.5)
            i += 1
            continue

        # 普通段落
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        add_inline(p, stripped, size=10.5)
        i += 1

    doc.save(out_path)
    print("saved", out_path)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
