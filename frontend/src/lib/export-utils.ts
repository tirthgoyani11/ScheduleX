import * as XLSX from "xlsx";
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

export async function exportFacultyPDF(tt: Timetable, facultyName: string) {
  const safeName = facultyName.replace(/\s+/g, "_");
  const filename = `Schedule_${safeName}.pdf`;
  await downloadPdf(
    `/export/faculty/${tt.timetable_id}?faculty_name=${encodeURIComponent(facultyName)}`,
    filename,
  );
}

export async function exportRoomPDF(tt: Timetable) {
  const filename = `Room_Allocation_Sem${tt.semester}_${tt.academic_year}.pdf`;
  await downloadPdf(`/export/room/${tt.timetable_id}`, filename);
}

// ── Excel Workbook (client-side) ─────────────────────────
export function exportExcelWorkbook(tt: Timetable, slots: TimeSlot[]) {
  const days = getDays(tt.entries);
  const batchNames = getBatchNames(tt.entries);
  const labPeriods = getLabPeriods(tt.entries);
  const lookup = buildLookup(tt.entries);
  const hasBatches = batchNames.length > 0;
  const numBatches = hasBatches ? batchNames.length : 1;

  const wb = XLSX.utils.book_new();

  // Sheet 1: Grid — GCET style with batch sub-columns for labs
  const headerRow1 = ["Time"];
  const headerRow2 = [""];
  for (const day of days) {
    if (hasBatches) {
      headerRow1.push(day.toUpperCase());
      for (let i = 1; i < numBatches; i++) headerRow1.push("");
      for (const bn of batchNames) headerRow2.push(bn);
    } else {
      headerRow1.push(day.toUpperCase());
      headerRow2.push("");
    }
  }

  const xlLabBlocks = detectLabBlocks(slots, days, lookup);

  const gridData: string[][] = [headerRow1];
  if (hasBatches) gridData.push(headerRow2);

  const xlLabMerges: XLSX.Range[] = [];
  const headerOffset = hasBatches ? 2 : 1;
  let xlRowIdx = headerOffset;

  for (const slot of slots) {
    const row: string[] = [`${slot.start_time}-${slot.end_time} ${slot.label}`];

    if (slot.slot_type === "break") {
      for (let i = 0; i < days.length * numBatches; i++) row.push(slot.label.toUpperCase());
      gridData.push(row);
      xlRowIdx++;
      continue;
    }

    const isLabSlot = labPeriods.has(slot.slot_order);
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
            row.push(entry ? `${entry.subject_name}\n${entry.faculty_name}\n${entry.room_name}${hours}` : "—");
            if (blockInfo.span > 1) {
              xlLabMerges.push({ s: { r: xlRowIdx, c: colIdx }, e: { r: xlRowIdx + blockInfo.span - 1, c: colIdx } });
            }
          } else if (blockInfo?.type === "skip") {
            row.push("");
          } else {
            const entry = cellEntries.find((e) => e.batch === bn);
            row.push(entry ? `${entry.subject_name}\n${entry.faculty_name}\n${entry.room_name}` : "—");
          }
          colIdx++;
        }
      } else if (hasBatches) {
        const e = cellEntries[0];
        row.push(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—");
        for (let i = 1; i < numBatches; i++) row.push("");
        colIdx += numBatches;
      } else {
        const e = cellEntries[0];
        row.push(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—");
        colIdx++;
      }
    }
    gridData.push(row);
    xlRowIdx++;
  }

  const wsGrid = XLSX.utils.aoa_to_sheet(gridData);
  wsGrid["!cols"] = [{ wch: 22 }, ...Array(days.length * numBatches).fill({ wch: 20 })];
  const allMerges: XLSX.Range[] = [...xlLabMerges];
  if (hasBatches) {
    let col = 1;
    for (let d = 0; d < days.length; d++) {
      if (numBatches > 1) {
        allMerges.push({ s: { r: 0, c: col }, e: { r: 0, c: col + numBatches - 1 } });
      }
      col += numBatches;
    }
  }
  if (allMerges.length > 0) wsGrid["!merges"] = allMerges;
  XLSX.utils.book_append_sheet(wb, wsGrid, "Grid");

  // Sheet 2: Faculty load
  const facultyMap = new Map<string, { subjects: Set<string>; periods: number }>();
  for (const e of tt.entries) {
    if (!facultyMap.has(e.faculty_name)) facultyMap.set(e.faculty_name, { subjects: new Set(), periods: 0 });
    const f = facultyMap.get(e.faculty_name)!;
    f.subjects.add(e.subject_name);
    f.periods++;
  }
  const facultyRows = [["Faculty", "Subjects", "Periods/week"]];
  for (const [name, info] of Array.from(facultyMap.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
    facultyRows.push([name, Array.from(info.subjects).join(", "), String(info.periods)]);
  }
  const wsFaculty = XLSX.utils.aoa_to_sheet(facultyRows);
  wsFaculty["!cols"] = [{ wch: 25 }, { wch: 40 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, wsFaculty, "Faculty");

  // Sheet 3: Room usage
  const roomMap = new Map<string, number>();
  for (const e of tt.entries) {
    roomMap.set(e.room_name, (roomMap.get(e.room_name) || 0) + 1);
  }
  const roomRows = [["Room", "Periods Used"]];
  for (const [name, count] of Array.from(roomMap.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
    roomRows.push([name, String(count)]);
  }
  const wsRoom = XLSX.utils.aoa_to_sheet(roomRows);
  wsRoom["!cols"] = [{ wch: 20 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, wsRoom, "Rooms");

  // Sheet 4: Summary
  const summaryRows = [
    ["Metric", "Value"],
    ["Semester", String(tt.semester)],
    ["Academic Year", tt.academic_year],
    ["Status", tt.status],
    ["Optimization Score", `${tt.optimization_score ?? "N/A"}/100`],
    ["Total Entries", String(tt.entries.length)],
    ["Theory Entries", String(tt.entries.filter((e) => !e.batch).length)],
    ["Lab Entries", String(tt.entries.filter((e) => e.batch).length)],
    ["Faculty Count", String(facultyMap.size)],
    ["Rooms Used", String(roomMap.size)],
  ];
  const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);
  wsSummary["!cols"] = [{ wch: 20 }, { wch: 25 }];
  XLSX.utils.book_append_sheet(wb, wsSummary, "Summary");

  XLSX.writeFile(wb, `Timetable_Sem${tt.semester}_${tt.academic_year}.xlsx`);
}
