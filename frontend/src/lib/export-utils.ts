import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import type { Timetable, TimetableEntry, TimeSlot } from "@/types";

const ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function getDays(entries: TimetableEntry[]) {
  const used = new Set(entries.map((e) => e.day));
  return ALL_DAYS.filter((d) => used.has(d));
}

function buildGrid(entries: TimetableEntry[], slots: TimeSlot[], days: string[]) {
  const lookup = new Map<string, TimetableEntry[]>();
  for (const e of entries) {
    const key = `${e.day}|${e.period}`;
    if (!lookup.has(key)) lookup.set(key, []);
    lookup.get(key)!.push(e);
  }

  const rows: string[][] = [];
  for (const slot of slots) {
    const row: string[] = [`${slot.start_time}-${slot.end_time}\n${slot.label}`];
    for (const day of days) {
      if (slot.slot_type === "break") {
        row.push(slot.label);
        continue;
      }
      const cellEntries = lookup.get(`${day}|${slot.slot_order}`) || [];
      if (cellEntries.length === 0) {
        row.push("—");
      } else if (cellEntries.length === 1 && !cellEntries[0].batch) {
        const e = cellEntries[0];
        row.push(`${e.subject_name}\n${e.faculty_name}\n${e.room_name}`);
      } else {
        // Multiple batch entries
        row.push(
          cellEntries
            .map((e) => `[${e.batch}] ${e.subject_name}\n${e.faculty_name} · ${e.room_name}`)
            .join("\n")
        );
      }
    }
    rows.push(row);
  }
  return rows;
}

// ── Department PDF ───────────────────────────────────────
export function exportDepartmentPDF(tt: Timetable, slots: TimeSlot[]) {
  const days = getDays(tt.entries);
  const rows = buildGrid(tt.entries, slots, days);

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });

  doc.setFontSize(14);
  doc.text(`Timetable — Semester ${tt.semester} · ${tt.academic_year}`, 14, 15);
  doc.setFontSize(9);
  doc.text(`Status: ${tt.status} | Score: ${tt.optimization_score ?? "N/A"}/100`, 14, 21);

  autoTable(doc, {
    startY: 26,
    head: [["Time", ...days]],
    body: rows,
    theme: "grid",
    styles: { fontSize: 7, cellPadding: 2, valign: "middle", overflow: "linebreak" },
    headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: "bold", halign: "center" },
    columnStyles: { 0: { cellWidth: 24, fontStyle: "bold" } },
    didParseCell(data) {
      // Highlight break rows
      if (data.section === "body" && data.row.raw) {
        const raw = data.row.raw as string[];
        if (raw[0]?.includes("Lunch") || raw[0]?.includes("Break")) {
          data.cell.styles.fillColor = [243, 244, 246];
          data.cell.styles.fontStyle = "italic";
        }
      }
    },
  });

  doc.save(`Timetable_Sem${tt.semester}_${tt.academic_year}.pdf`);
}

// ── Excel Workbook ───────────────────────────────────────
export function exportExcelWorkbook(tt: Timetable, slots: TimeSlot[]) {
  const days = getDays(tt.entries);
  const rows = buildGrid(tt.entries, slots, days);
  const wb = XLSX.utils.book_new();

  // Sheet 1: Grid
  const gridData = [["Time", ...days], ...rows];
  const wsGrid = XLSX.utils.aoa_to_sheet(gridData);
  wsGrid["!cols"] = [{ wch: 18 }, ...days.map(() => ({ wch: 28 }))];
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

// ── Faculty Schedule PDF ─────────────────────────────────
export function exportFacultyPDF(
  tt: Timetable,
  slots: TimeSlot[],
  facultyName: string
) {
  const entries = tt.entries.filter((e) => e.faculty_name === facultyName);
  const days = getDays(entries.length ? entries : tt.entries);

  const lookup = new Map<string, TimetableEntry>();
  for (const e of entries) {
    lookup.set(`${e.day}|${e.period}`, e);
  }

  const rows: string[][] = [];
  for (const slot of slots) {
    const row: string[] = [`${slot.start_time}-${slot.end_time}`];
    for (const day of days) {
      if (slot.slot_type === "break") {
        row.push(slot.label);
        continue;
      }
      const entry = lookup.get(`${day}|${slot.slot_order}`);
      row.push(entry ? `${entry.subject_name}\n${entry.room_name}${entry.batch ? `\n(${entry.batch})` : ""}` : "—");
    }
    rows.push(row);
  }

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  doc.setFontSize(14);
  doc.text(`Faculty Schedule — ${facultyName}`, 14, 15);
  doc.setFontSize(9);
  doc.text(`Semester ${tt.semester} · ${tt.academic_year} | Periods: ${entries.length}`, 14, 21);

  autoTable(doc, {
    startY: 26,
    head: [["Time", ...days]],
    body: rows,
    theme: "grid",
    styles: { fontSize: 8, cellPadding: 2.5, valign: "middle", overflow: "linebreak" },
    headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: "bold", halign: "center" },
    columnStyles: { 0: { cellWidth: 22, fontStyle: "bold" } },
  });

  doc.save(`Schedule_${facultyName.replace(/\s+/g, "_")}.pdf`);
}

// ── Room Allocation PDF ──────────────────────────────────
export function exportRoomPDF(tt: Timetable, slots: TimeSlot[]) {
  const days = getDays(tt.entries);
  const roomNames = Array.from(new Set(tt.entries.map((e) => e.room_name))).sort();

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  doc.setFontSize(14);
  doc.text(`Room Allocation — Semester ${tt.semester} · ${tt.academic_year}`, 14, 15);

  let startY = 22;

  for (const roomName of roomNames) {
    const roomEntries = tt.entries.filter((e) => e.room_name === roomName);
    const lookup = new Map<string, TimetableEntry>();
    for (const e of roomEntries) {
      lookup.set(`${e.day}|${e.period}`, e);
    }

    const rows: string[][] = [];
    for (const slot of slots) {
      const row: string[] = [`${slot.start_time}-${slot.end_time}`];
      for (const day of days) {
        if (slot.slot_type === "break") { row.push("—"); continue; }
        const entry = lookup.get(`${day}|${slot.slot_order}`);
        row.push(entry ? `${entry.subject_name}\n${entry.faculty_name}${entry.batch ? `\n(${entry.batch})` : ""}` : "—");
      }
      rows.push(row);
    }

    // Check if we need a new page
    if (startY > 140) {
      doc.addPage();
      startY = 15;
    }

    doc.setFontSize(11);
    doc.text(roomName, 14, startY);
    startY += 3;

    autoTable(doc, {
      startY,
      head: [["Time", ...days]],
      body: rows,
      theme: "grid",
      styles: { fontSize: 7, cellPadding: 1.5, valign: "middle", overflow: "linebreak" },
      headStyles: { fillColor: [16, 185, 129], textColor: 255, fontStyle: "bold", halign: "center" },
      columnStyles: { 0: { cellWidth: 20, fontStyle: "bold" } },
    });

    startY = (doc as any).lastAutoTable.finalY + 8;
  }

  doc.save(`Room_Allocation_Sem${tt.semester}_${tt.academic_year}.pdf`);
}
