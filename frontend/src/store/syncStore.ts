import { create } from "zustand";
import { syncService, SyncTaskRecord, SyncParams } from "../services/syncService";

export type SyncStatus = "idle" | "running" | "completed" | "failed";

export interface CurrentSync {
  taskId: string;
  sourceType: string;
  dataType: string;
  status: SyncStatus;
  processed: number;
  total: number;
  success: number;
  failed: number;
  errorMessage: string | null;
  durationMs: number | null;
}

interface SyncState {
  currentSync: CurrentSync | null;
  syncStatus: SyncStatus;
  syncHistory: SyncTaskRecord[];
  historyTotal: number;
  historyPage: number;
  isLoadingHistory: boolean;

  // Actions
  startSync: (sourceType: string, dataType: string) => void;
  updateProgress: (data: any) => void;
  completeSync: (data: any) => void;
  failSync: (error: string) => void;
  resetSync: () => void;
  loadHistory: (page?: number, sourceType?: string, status?: string) => Promise<void>;
  retryTask: (taskId: string) => void;
}

export const useSyncStore = create<SyncState>((set, get) => ({
  currentSync: null,
  syncStatus: "idle",
  syncHistory: [],
  historyTotal: 0,
  historyPage: 1,
  isLoadingHistory: false,

  startSync: (sourceType: string, dataType: string) => {
    set({
      currentSync: {
        taskId: "",
        sourceType,
        dataType,
        status: "running",
        processed: 0,
        total: 0,
        success: 0,
        failed: 0,
        errorMessage: null,
        durationMs: null,
      },
      syncStatus: "running",
    });
  },

  updateProgress: (data: any) => {
    set((state) => ({
      currentSync: state.currentSync
        ? {
            ...state.currentSync,
            taskId: data.task_id || state.currentSync.taskId,
            total: data.total ?? state.currentSync.total,
            processed: data.processed ?? state.currentSync.processed,
            success: data.success ?? state.currentSync.success,
            failed: data.failed ?? state.currentSync.failed,
          }
        : null,
    }));
  },

  completeSync: (data: any) => {
    set((state) => ({
      currentSync: state.currentSync
        ? {
            ...state.currentSync,
            status: "completed",
            processed: data.processed ?? state.currentSync.processed,
            success: data.success ?? state.currentSync.success,
            failed: data.failed ?? state.currentSync.failed,
            durationMs: data.duration_ms ?? null,
          }
        : null,
      syncStatus: "completed",
    }));
  },

  failSync: (error: string) => {
    set({
      currentSync: {
        taskId: "",
        sourceType: "",
        dataType: "",
        status: "failed",
        processed: 0,
        total: 0,
        success: 0,
        failed: 0,
        errorMessage: error,
        durationMs: null,
      },
      syncStatus: "failed",
    });
  },

  resetSync: () => {
    set({
      currentSync: null,
      syncStatus: "idle",
    });
  },

  loadHistory: async (page = 1, sourceType?: string, status?: string) => {
    set({ isLoadingHistory: true });
    try {
      const result = await syncService.listSyncTasks(page, 20, sourceType, status);
      set({
        syncHistory: result.items,
        historyTotal: result.total,
        historyPage: page,
      });
    } catch (err) {
      console.error("Failed to load sync history:", err);
    } finally {
      set({ isLoadingHistory: false });
    }
  },

  retryTask: (taskId: string) => {
    // Trigger a new sync - the retry API will handle it
    syncService.retryTask(taskId);
  },
}));
