import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, api } from "@/lib/api-client";
import { toast } from "sonner";

interface ImportCategory {
  key: string;
  label: string;
  columns: string;
}

interface ImportResult {
  category: string;
  inserted: number;
  skipped: number;
  total: number;
  warnings?: string[];
}

interface ExcelImportResponse {
  results: ImportResult[];
  sheets_processed: number;
}

export function usePdfImport() {
  const queryClient = useQueryClient();

  const { data: categories = [], isLoading: categoriesLoading } = useQuery<ImportCategory[]>({
    queryKey: ["pdf-import-categories"],
    queryFn: () => api.get("/pdf-import/categories"),
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["departments"] });
    queryClient.invalidateQueries({ queryKey: ["faculty"] });
    queryClient.invalidateQueries({ queryKey: ["subjects"] });
    queryClient.invalidateQueries({ queryKey: ["rooms"] });
    queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    queryClient.invalidateQueries({ queryKey: ["batches"] });
  };

  const uploadExcelMutation = useMutation<ExcelImportResponse, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiClient.post("/pdf-import/upload-excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: (data) => {
      const total = data.results.reduce((s, r) => s + r.inserted, 0);
      toast.success(
        `Imported ${total} records across ${data.sheets_processed} categories`
      );
      invalidateAll();
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || "Upload failed";
      toast.error(detail);
    },
  });

  return {
    categories,
    categoriesLoading,
    uploadExcel: uploadExcelMutation.mutateAsync,
    isUploadingExcel: uploadExcelMutation.isPending,
  };
}
