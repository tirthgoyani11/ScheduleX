import { create } from "zustand";

interface SetupState {
  currentSemester: number;
  setSemester: (s: number) => void;
}

export const useSetupStore = create<SetupState>((set) => ({
  currentSemester: 3,
  setSemester: (s) => set({ currentSemester: s }),
}));
