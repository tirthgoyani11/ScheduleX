import { create } from "zustand";

interface TimetableStoreState {
  generatingStep: number;
  selectedSemester: number;
  divisions: string[];
  workingDays: string[];
  setStep: (s: number) => void;
  setSemester: (s: number) => void;
  setDivisions: (d: string[]) => void;
  setWorkingDays: (d: string[]) => void;
  reset: () => void;
}

export const useTimetableStore = create<TimetableStoreState>((set) => ({
  generatingStep: 1,
  selectedSemester: 3,
  divisions: ["A"],
  workingDays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
  setStep: (s) => set({ generatingStep: s }),
  setSemester: (s) => set({ selectedSemester: s }),
  setDivisions: (d) => set({ divisions: d }),
  setWorkingDays: (d) => set({ workingDays: d }),
  reset: () => set({ generatingStep: 1, selectedSemester: 3, divisions: ["A"], workingDays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] }),
}));
