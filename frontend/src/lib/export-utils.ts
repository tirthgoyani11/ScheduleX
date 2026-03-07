import XLSX from "xlsx-js-style";
import { apiClient } from "@/lib/api-client";
import type { Timetable, TimetableEntry, TimeSlot } from "@/types";

const ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// ── Helpers for Excel export (client-side) ───────────────
function getDays(entries: TimetableEntry[]) {
  const used = new Set(entries.map((e) => e.day));
  return ALL_DAYS.filter((d) => used.has(d));
}

function getBatchNames(entries: TimetableEntry[]) {
  const names = new Set<string>();
  entries.forEach((e) => { if (e.batch) names.add(e.batch); });
  return Array.from(names).sort();
}

function getLabPeriods(entries: TimetableEntry[]) {
  const periods = new Set<number>();
  entries.forEach((e) => { if (e.batch) periods.add(e.period); });
  return periods;
}

function buildLookup(entries: TimetableEntry[]) {
  const map = new Map<string, TimetableEntry[]>();
  for (const e of entries) {
    const key = `${e.day}|${e.period}`;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(e);
  }
  return map;
}

function detectLabBlocks(
  slots: TimeSlot[],
  days: string[],
  lookup: Map<string, TimetableEntry[]>
) {
  const result = new Map<string, { type: "start"; span: number; endTime: string } | { type: "skip" }>();
  const nonBreak = slots.filter((s) => s.slot_type !== "break").sort((a, b) => a.slot_order - b.slot_order);

  for (const day of days) {
    let i = 0;
    while (i < nonBreak.length) {
      const curr = nonBreak[i];
      const currBatch = (lookup.get(`${day}|${curr.slot_order}`) || []).filter((e) => e.batch);
      if (currBatch.length === 0) { i++; continue; }

      const currSig = currBatch
        .map((e) => `${e.subject_name}|${e.batch}|${e.faculty_name}|${e.room_name}`)
        .sort()
        .join(",");

      let span = 1;
      while (i + span < nonBreak.length) {
        const next = nonBreak[i + span];
        const nextBatch = (lookup.get(`${day}|${next.slot_order}`) || []).filter((e) => e.batch);
        const nextSig = nextBatch
          .map((e) => `${e.subject_name}|${e.batch}|${e.faculty_name}|${e.room_name}`)
          .sort()
          .join(",");
        if (nextSig === currSig) span++;
        else break;
      }

      if (span > 1) {
        const lastSlot = nonBreak[i + span - 1];
        result.set(`${day}|${curr.slot_order}`, { type: "start", span, endTime: lastSlot.end_time });
        for (let j = 1; j < span; j++) {
          result.set(`${day}|${nonBreak[i + j].slot_order}`, { type: "skip" });
        }
        i += span;
      } else {
        i++;
      }
    }
  }
  return result;
}

// ── PDF Downloads (server-side via WeasyPrint) ───────────
async function downloadPdf(url: string, filename: string) {
  const response = await apiClient.get(url, { responseType: "blob" });
  const blob = new Blob([response.data], { type: "application/pdf" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

export async function exportDepartmentPDF(tt: Timetable) {
  const filename = `Timetable_Sem${tt.semester}_${tt.academic_year}.pdf`;
  await downloadPdf(`/export/department/${tt.timetable_id}`, filename);
}

export async function exportFacultyPDF(tt: Timetable) {
  const filename = `Faculty_Schedules_Sem${tt.semester}_${tt.academic_year}.pdf`;
  await downloadPdf(`/export/faculty/${tt.timetable_id}`, filename);
}

export async function exportRoomPDF(tt: Timetable) {
  const filename = `Room_Allocation_Sem${tt.semester}_${tt.academic_year}.pdf`;
  await downloadPdf(`/export/room/${tt.timetable_id}`, filename);
}

// ── Excel Workbook (client-side) ─────────────────────────

// Style constants
const BORDER_THIN = { style: "thin", color: { rgb: "B0B0B0" } } as const;
const BORDERS_ALL = { top: BORDER_THIN, bottom: BORDER_THIN, left: BORDER_THIN, right: BORDER_THIN } as const;

const S_HEADER: XLSX.CellStyle = {
  font: { bold: true, color: { rgb: "FFFFFF" }, sz: 11 },
  fill: { fgColor: { rgb: "1E40AF" } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_HEADER_GREEN: XLSX.CellStyle = {
  font: { bold: true, color: { rgb: "FFFFFF" }, sz: 11 },
  fill: { fgColor: { rgb: "0F766E" } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_TIME: XLSX.CellStyle = {
  font: { bold: true, sz: 9 },
  fill: { fgColor: { rgb: "F1F5F9" } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_BREAK: XLSX.CellStyle = {
  font: { bold: true, sz: 10, color: { rgb: "92400E" } },
  fill: { fgColor: { rgb: "FEF9C3" } },
  alignment: { horizontal: "center", vertical: "center" },
  border: BORDERS_ALL,
};
const S_CELL: XLSX.CellStyle = {
  font: { sz: 9 },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_CELL_ALT: XLSX.CellStyle = {
  ...S_CELL,
  fill: { fgColor: { rgb: "F8FAFC" } },
};
const S_LAB: XLSX.CellStyle = {
  font: { sz: 9, color: { rgb: "0E7490" } },
  fill: { fgColor: { rgb: "ECFEFF" } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_EMPTY: XLSX.CellStyle = {
  font: { sz: 9, color: { rgb: "CBD5E1" } },
  alignment: { horizontal: "center", vertical: "center" },
  border: BORDERS_ALL,
};
const S_METRIC: XLSX.CellStyle = {
  font: { bold: true, sz: 10 },
  fill: { fgColor: { rgb: "F1F5F9" } },
  alignment: { vertical: "center" },
  border: BORDERS_ALL,
};
const S_VALUE: XLSX.CellStyle = {
  font: { sz: 10 },
  alignment: { vertical: "center" },
  border: BORDERS_ALL,
};
const S_ROW: XLSX.CellStyle = {
  font: { sz: 10 },
  alignment: { vertical: "center", wrapText: true },
  border: BORDERS_ALL,
};
const S_ROW_ALT: XLSX.CellStyle = {
  ...S_ROW,
  fill: { fgColor: { rgb: "F8FAFC" } },
};

function styledCell(v: string | number, s: XLSX.CellStyle): XLSX.CellObject {
  return { v, t: typeof v === "number" ? "n" : "s", s };
}

export function exportExcelWorkbook(tt: Timetable, slots: TimeSlot[]) {
  const days = getDays(tt.entries);
  const batchNames = getBatchNames(tt.entries);
  const labPeriods = getLabPeriods(tt.entries);
  const lookup = buildLookup(tt.entries);
  const hasBatches = batchNames.length > 0;
  const numBatches = hasBatches ? batchNames.length : 1;

  const wb = XLSX.utils.book_new();

  // ── Sheet 1: Grid ──────────────────────────────────────
  const gridData: XLSX.CellObject[][] = [];

  // Title row
  const titleRow: XLSX.CellObject[] = [styledCell(
    `Timetable — Sem ${tt.semester} — ${tt.academic_year}`,
    { font: { bold: true, sz: 14, color: { rgb: "1E40AF" } }, alignment: { horizontal: "left", vertical: "center" } },
  )];
  gridData.push(titleRow);

  // Header row 1 (days)
  const hRow1: XLSX.CellObject[] = [styledCell("TIME", S_HEADER)];
  for (const day of days) {
    hRow1.push(styledCell(day.toUpperCase(), S_HEADER));
    if (hasBatches) for (let i = 1; i < numBatches; i++) hRow1.push(styledCell("", S_HEADER));
  }
  gridData.push(hRow1);

  // Header row 2 (batch names) if batches exist
  if (hasBatches) {
    const hRow2: XLSX.CellObject[] = [styledCell("", S_HEADER)];
    for (const _day of days) {
      for (const bn of batchNames) hRow2.push(styledCell(bn, { ...S_HEADER, font: { ...S_HEADER.font!, sz: 9, italic: true } }));
    }
    gridData.push(hRow2);
  }

  const xlLabBlocks = detectLabBlocks(slots, days, lookup);
  const allMerges: XLSX.Range[] = [];
  const headerOffset = hasBatches ? 3 : 2; // +1 for title row
  let xlRowIdx = headerOffset;

  // Title merge
  allMerges.push({ s: { r: 0, c: 0 }, e: { r: 0, c: days.length * numBatches } });

  let dataRowCount = 0;
  for (const slot of slots) {
    const row: XLSX.CellObject[] = [styledCell(`${slot.start_time}–${slot.end_time}`, S_TIME)];

    if (slot.slot_type === "break") {
      for (let i = 0; i < days.length * numBatches; i++) row.push(styledCell(`☕ ${slot.label.toUpperCase()}`, S_BREAK));
      gridData.push(row);
      xlRowIdx++;
      continue;
    }

    const isLabSlot = labPeriods.has(slot.slot_order);
    const isAlt = dataRowCount % 2 === 1;
    const cellStyle = isAlt ? S_CELL_ALT : S_CELL;
    let colIdx = 1;

    for (const day of days) {
      const blockInfo = xlLabBlocks.get(`${day}|${slot.slot_order}`);
      const cellEntries = lookup.get(`${day}|${slot.slot_order}`) || [];
      const cellHasLabs = cellEntries.some((e) => e.batch);

      if (hasBatches && isLabSlot && cellHasLabs) {
        for (const bn of batchNames) {
          if (blockInfo?.type === "start") {
            const entry = cellEntries.find((e) => e.batch === bn);
            const hours = ` (${blockInfo.span}h)`;
            row.push(styledCell(entry ? `${entry.subject_name}\n${entry.faculty_name}\n${entry.room_name}${hours}` : "—", entry ? S_LAB : S_EMPTY));
            if (blockInfo.span > 1) {
              allMerges.push({ s: { r: xlRowIdx, c: colIdx }, e: { r: xlRowIdx + blockInfo.span - 1, c: colIdx } });
            }
          } else if (blockInfo?.type === "skip") {
            row.push(styledCell("", S_LAB));
          } else {
            const entry = cellEntries.find((e) => e.batch === bn);
            row.push(styledCell(entry ? `${entry.subject_name}\n${entry.faculty_name}\n${entry.room_name}` : "—", entry ? S_LAB : S_EMPTY));
          }
          colIdx++;
        }
      } else if (hasBatches) {
        const e = cellEntries[0];
        row.push(styledCell(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—", e ? cellStyle : S_EMPTY));
        for (let i = 1; i < numBatches; i++) row.push(styledCell("", cellStyle));
        colIdx += numBatches;
      } else {
        const e = cellEntries[0];
        row.push(styledCell(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—", e ? cellStyle : S_EMPTY));
        colIdx++;
      }
    }
    gridData.push(row);
    xlRowIdx++;
    dataRowCount++;
  }

  const wsGrid = XLSX.utils.aoa_to_sheet(gridData);
  wsGrid["!cols"] = [{ wch: 16 }, ...Array(days.length * numBatches).fill({ wch: 22 })];
  wsGrid["!rows"] = [{ hpt: 28 }]; // title row height

  // Day header merges
  if (hasBatches) {
    let col = 1;
    for (let d = 0; d < days.length; d++) {
      if (numBatches > 1) {
        allMerges.push({ s: { r: 1, c: col }, e: { r: 1, c: col + numBatches - 1 } });
      }
      col += numBatches;
    }
  }
  if (allMerges.length > 0) wsGrid["!merges"] = allMerges;
  XLSX.utils.book_append_sheet(wb, wsGrid, "Grid");

  // ── Sheet 2: Faculty Load ──────────────────────────────
  const facultyMap = new Map<string, { subjects: Set<string>; periods: number }>();
  for (const e of tt.entries) {
    if (!facultyMap.has(e.faculty_name)) facultyMap.set(e.faculty_name, { subjects: new Set(), periods: 0 });
    const f = facultyMap.get(e.faculty_name)!;
    f.subjects.add(e.subject_name);
    f.periods++;
  }
  const facData: XLSX.CellObject[][] = [
    [styledCell("Faculty", S_HEADER), styledCell("Subjects", S_HEADER), styledCell("Periods/Week", S_HEADER)],
  ];
  let facIdx = 0;
  for (const [name, info] of Array.from(facultyMap.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
    const rs = facIdx % 2 === 1 ? S_ROW_ALT : S_ROW;
    facData.push([
      styledCell(name, { ...rs, font: { ...rs.font!, bold: true } }),
      styledCell(Array.from(info.subjects).join(", "), rs),
      styledCell(info.periods, { ...rs, alignment: { horizontal: "center", vertical: "center" } }),
    ]);
    facIdx++;
  }
  const wsFaculty = XLSX.utils.aoa_to_sheet(facData);
  wsFaculty["!cols"] = [{ wch: 28 }, { wch: 45 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, wsFaculty, "Faculty");

  // ── Sheet 3: Room Usage ────────────────────────────────
  const roomMap = new Map<string, number>();
  for (const e of tt.entries) {
    roomMap.set(e.room_name, (roomMap.get(e.room_name) || 0) + 1);
  }
  const roomData: XLSX.CellObject[][] = [
    [styledCell("Room", S_HEADER_GREEN), styledCell("Periods Used", S_HEADER_GREEN)],
  ];
  let roomIdx = 0;
  for (const [name, count] of Array.from(roomMap.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
    const rs = roomIdx % 2 === 1 ? S_ROW_ALT : S_ROW;
    roomData.push([
      styledCell(name, { ...rs, font: { ...rs.font!, bold: true } }),
      styledCell(count, { ...rs, alignment: { horizontal: "center", vertical: "center" } }),
    ]);
    roomIdx++;
  }
  const wsRoom = XLSX.utils.aoa_to_sheet(roomData);
  wsRoom["!cols"] = [{ wch: 24 }, { wch: 16 }];
  XLSX.utils.book_append_sheet(wb, wsRoom, "Rooms");

  // ── Sheet 4: Summary ──────────────────────────────────
  const summaryData: XLSX.CellObject[][] = [
    [styledCell("Metric", S_HEADER), styledCell("Value", S_HEADER)],
    [styledCell("Semester", S_METRIC), styledCell(tt.semester, S_VALUE)],
    [styledCell("Academic Year", S_METRIC), styledCell(tt.academic_year, S_VALUE)],
    [styledCell("Status", S_METRIC), styledCell(tt.status, S_VALUE)],
    [styledCell("Optimization Score", S_METRIC), styledCell(`${tt.optimization_score ?? "N/A"}/100`, S_VALUE)],
    [styledCell("Total Entries", S_METRIC), styledCell(tt.entries.length, S_VALUE)],
    [styledCell("Theory Entries", S_METRIC), styledCell(tt.entries.filter((e) => !e.batch).length, S_VALUE)],
    [styledCell("Lab Entries", S_METRIC), styledCell(tt.entries.filter((e) => e.batch).length, S_VALUE)],
    [styledCell("Faculty Count", S_METRIC), styledCell(facultyMap.size, S_VALUE)],
    [styledCell("Rooms Used", S_METRIC), styledCell(roomMap.size, S_VALUE)],
  ];
  const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
  wsSummary["!cols"] = [{ wch: 22 }, { wch: 28 }];
  XLSX.utils.book_append_sheet(wb, wsSummary, "Summary");

  XLSX.writeFile(wb, `Timetable_Sem${tt.semester}_${tt.academic_year}.xlsx`);
}
