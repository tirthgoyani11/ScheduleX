import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import type { Timetable, TimetableEntry, TimeSlot, Subject, Faculty } from "@/types";

const ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_SHORT: Record<string, string> = {
  Monday: "MONDAY", Tuesday: "TUESDAY", Wednesday: "WEDNESDAY",
  Thursday: "THURSDAY", Friday: "FRIDAY", Saturday: "SATURDAY",
};

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

// Generate faculty initials/abbreviation from name
function facultyAbbr(name: string) {
  const parts = name.split(/\s+/);
  if (parts.length <= 1) return name.slice(0, 4).toUpperCase();
  // Use first letter of first name + last name, e.g. "Dr. Rajesh Patel" → "RP"
  const filtered = parts.filter((p) => !p.endsWith("."));
  if (filtered.length === 0) return parts.map((p) => p[0]).join("").toUpperCase();
  return filtered.map((p) => p[0]).join("").toUpperCase();
}

// ── GCET-Style Department PDF ────────────────────────────
export function exportDepartmentPDF(
  tt: Timetable,
  slots: TimeSlot[],
  subjects?: Subject[],
  faculty?: Faculty[],
  collegeName?: string,
  deptName?: string
) {
  const days = getDays(tt.entries);
  const batchNames = getBatchNames(tt.entries);
  const labPeriods = getLabPeriods(tt.entries);
  const lookup = buildLookup(tt.entries);
  const hasBatches = batchNames.length > 0;

  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const margin = 5;

  // ── Header Section (compact) ──
  const college = collegeName || "Charutar Vidya Mandal University";
  const dept = deptName || "Department of Computer Engineering";

  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text(college, pageW / 2, 8, { align: "center" });

  doc.setFontSize(7.5);
  doc.setFont("helvetica", "normal");
  doc.text(`Timetable For ${tt.academic_year}  |  Program: ${dept}, Semester: ${tt.semester}`, pageW / 2, 13, { align: "center" });

  // Info row
  doc.setFontSize(6);
  const dateStr = tt.created_at ? new Date(tt.created_at).toLocaleDateString("en-IN") : new Date().toLocaleDateString("en-IN");
  doc.text(`Status: ${tt.status}     Score: ${tt.optimization_score ?? "N/A"}/100`, margin, 17);
  doc.text(`Generated: ${dateStr}`, pageW - margin, 17, { align: "right" });

  // ── Build the main timetable grid ──
  // For lab periods, each day gets split into batch sub-columns
  const numBatches = hasBatches ? batchNames.length : 1;

  // Build header row(s)
  // Row 1: Time + day names (spanning batch columns)
  const headerRow1: any[] = [{ content: "Time", rowSpan: hasBatches ? 2 : 1, styles: { halign: "center", valign: "middle" } }];
  for (const day of days) {
    headerRow1.push({
      content: DAY_SHORT[day] || day.toUpperCase(),
      colSpan: hasBatches ? numBatches : 1,
      styles: { halign: "center" },
    });
  }

  // Row 2: batch names under each day (only if we have batches)
  const headerRow2: any[] = [];
  if (hasBatches) {
    for (const _day of days) {
      for (const bn of batchNames) {
        headerRow2.push({ content: bn, styles: { halign: "center", fontSize: 5.5 } });
      }
    }
  }

  const headRows = hasBatches ? [headerRow1, headerRow2] : [headerRow1];

  // Build body rows
  const bodyRows: any[][] = [];
  for (const slot of slots) {
    const row: any[] = [];

    // Time cell
    row.push({
      content: `${slot.start_time} to ${slot.end_time}\n${slot.label}`,
      styles: { fontStyle: "bold", fontSize: 5, halign: "center", valign: "middle" },
    });

    if (slot.slot_type === "break") {
      // Break row — single cell spanning all columns
      row.push({
        content: slot.label.toUpperCase(),
        colSpan: days.length * (hasBatches ? numBatches : 1),
        styles: {
          halign: "center", valign: "middle", fontStyle: "bold",
          fillColor: [255, 255, 200], fontSize: 6,
        },
      });
      bodyRows.push(row);
      continue;
    }

    const isLabSlot = labPeriods.has(slot.slot_order);

    for (const day of days) {
      const cellEntries = lookup.get(`${day}|${slot.slot_order}`) || [];

      if (hasBatches && isLabSlot) {
        // Lab period — one sub-cell per batch
        for (const bn of batchNames) {
          const entry = cellEntries.find((e) => e.batch === bn);
          if (entry) {
            row.push({
              content: `${entry.subject_name}\n${facultyAbbr(entry.faculty_name)}\n${entry.room_name}`,
              styles: { fontSize: 4.5, halign: "center", valign: "middle", cellPadding: 0.5 },
            });
          } else {
            row.push({ content: "—", styles: { halign: "center", valign: "middle", textColor: [180, 180, 180] } });
          }
        }
      } else if (hasBatches) {
        // Theory period — merge across all batch columns
        if (cellEntries.length > 0) {
          const e = cellEntries[0];
          row.push({
            content: `${e.subject_name}\n${facultyAbbr(e.faculty_name)}\n${e.room_name}`,
            colSpan: numBatches,
            styles: { fontSize: 5.5, halign: "center", valign: "middle" },
          });
        } else {
          row.push({
            content: "—",
            colSpan: numBatches,
            styles: { halign: "center", valign: "middle", textColor: [180, 180, 180] },
          });
        }
      } else {
        // No batches at all
        if (cellEntries.length > 0) {
          const e = cellEntries[0];
          row.push({
            content: `${e.subject_name}\n${facultyAbbr(e.faculty_name)}\n${e.room_name}`,
            styles: { fontSize: 5.5, halign: "center", valign: "middle" },
          });
        } else {
          row.push({ content: "—", styles: { halign: "center", valign: "middle", textColor: [180, 180, 180] } });
        }
      }
    }

    bodyRows.push(row);
  }

  autoTable(doc, {
    startY: 19,
    head: headRows,
    body: bodyRows,
    theme: "grid",
    margin: { left: margin, right: margin },
    styles: { fontSize: 5, cellPadding: 0.8, valign: "middle", overflow: "linebreak", lineWidth: 0.15 },
    headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: "bold", halign: "center", fontSize: 5.5, minCellHeight: 5 },
    columnStyles: { 0: { cellWidth: 18 } },
    tableLineColor: [0, 0, 0],
    tableLineWidth: 0.15,
  });

  let curY = (doc as any).lastAutoTable.finalY + 3;

  // ── Subject Legend Table ──
  const subjectSet = new Map<string, TimetableEntry>();
  for (const e of tt.entries) {
    if (!subjectSet.has(e.subject_name)) subjectSet.set(e.subject_name, e);
  }

  // Try to match with subjects data for L/P/T/C info
  const subjectRows: string[][] = [];
  for (const [name, entry] of subjectSet) {
    const matched = subjects?.find((s) => s.name === name);
    if (matched) {
      subjectRows.push([
        matched.subject_code,
        matched.name,
        String(matched.lecture_hours || matched.weekly_periods),
        String(matched.lab_hours || 0),
        "0",
        String(matched.credits),
      ]);
    } else {
      const isLab = entry.entry_type === "lab" || !!entry.batch;
      subjectRows.push([
        "—",
        name,
        isLab ? "0" : "3",
        isLab ? "2" : "0",
        "0",
        "—",
      ]);
    }
  }

  if (subjectRows.length > 0) {
    doc.setFontSize(6.5);
    doc.setFont("helvetica", "bold");
    doc.text("Subject Details:", margin, curY);
    curY += 1;

    autoTable(doc, {
      startY: curY,
      head: [["SUBJECT CODE", "NAME OF SUBJECT", "L", "P", "T", "C"]],
      body: subjectRows,
      theme: "grid",
      margin: { left: margin },
      styles: { fontSize: 5.5, cellPadding: 0.7 },
      headStyles: { fillColor: [255, 255, 0], textColor: 0, fontStyle: "bold", halign: "center", fontSize: 5.5 },
      columnStyles: {
        0: { cellWidth: 20, halign: "center" },
        1: { cellWidth: 55 },
        2: { cellWidth: 8, halign: "center" },
        3: { cellWidth: 8, halign: "center" },
        4: { cellWidth: 8, halign: "center" },
        5: { cellWidth: 8, halign: "center" },
      },
      tableWidth: "wrap",
      tableLineColor: [0, 0, 0],
      tableLineWidth: 0.15,
    });

    curY = (doc as any).lastAutoTable.finalY + 2;
  }

  // ── Faculty Legend (inline) ──
  const facultyNames = Array.from(new Set(tt.entries.map((e) => e.faculty_name))).sort();
  if (facultyNames.length > 0) {
    doc.setFontSize(6);
    doc.setFont("helvetica", "bold");
    doc.text("Faculty:", margin, curY);
    curY += 3;

    const legendParts = facultyNames.map((fn) => `${facultyAbbr(fn)} - ${fn}`);
    // Lay out in rows, ~3 per row with spacing
    const colW = 90;
    const cols = 3;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(5.5);
    for (let i = 0; i < legendParts.length; i += cols) {
      for (let c = 0; c < cols && i + c < legendParts.length; c++) {
        doc.text(legendParts[i + c], margin + c * colW, curY);
      }
      curY += 3.5;
    }
    curY += 1;
  }

  // ── Footer ──
  doc.setFontSize(6);
  doc.setFont("helvetica", "normal");
  doc.text("Prepared by: ___________________", margin, curY);
  doc.text("Verified by HOD: ___________________", pageW / 2 - 30, curY);
  doc.text("Principal/Director: ___________________", pageW - margin - 55, curY);

  doc.save(`Timetable_Sem${tt.semester}_${tt.academic_year}.pdf`);
}

// ── Excel Workbook ───────────────────────────────────────
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

  const gridData: string[][] = [headerRow1];
  if (hasBatches) gridData.push(headerRow2);

  for (const slot of slots) {
    const row: string[] = [`${slot.start_time}-${slot.end_time} ${slot.label}`];
    if (slot.slot_type === "break") {
      for (let i = 0; i < days.length * numBatches; i++) row.push(slot.label.toUpperCase());
      gridData.push(row);
      continue;
    }
    const isLabSlot = labPeriods.has(slot.slot_order);

    for (const day of days) {
      const cellEntries = lookup.get(`${day}|${slot.slot_order}`) || [];
      if (hasBatches && isLabSlot) {
        for (const bn of batchNames) {
          const entry = cellEntries.find((e) => e.batch === bn);
          row.push(entry ? `${entry.subject_name}\n${entry.faculty_name}\n${entry.room_name}` : "—");
        }
      } else if (hasBatches) {
        const e = cellEntries[0];
        row.push(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—");
        for (let i = 1; i < numBatches; i++) row.push("");
      } else {
        const e = cellEntries[0];
        row.push(e ? `${e.subject_name}\n${e.faculty_name}\n${e.room_name}` : "—");
      }
    }
    gridData.push(row);
  }

  const wsGrid = XLSX.utils.aoa_to_sheet(gridData);
  wsGrid["!cols"] = [{ wch: 22 }, ...Array(days.length * numBatches).fill({ wch: 20 })];
  // Merge header cells for day names spanning batch columns
  if (hasBatches) {
    const merges: XLSX.Range[] = [];
    let col = 1;
    for (let d = 0; d < days.length; d++) {
      if (numBatches > 1) {
        merges.push({ s: { r: 0, c: col }, e: { r: 0, c: col + numBatches - 1 } });
      }
      col += numBatches;
    }
    wsGrid["!merges"] = merges;
  }
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
