import { useSearchParams } from "react-router-dom";
import { compactParams } from "@/lib/utils";
import type { ListParams } from "@/types/common";

export function usePagedParams(defaultPageSize = 20) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = Object.fromEntries(searchParams.entries()) as Record<string, string>;
  const page = Number(params.page || 1);
  const pageSize = Number(params.page_size || defaultPageSize);

  function patch(next: Record<string, unknown>, resetPage = true) {
    setSearchParams(compactParams({ ...params, ...(resetPage ? { page: 1 } : {}), ...next }));
  }

  return {
    params: { ...params, page, page_size: pageSize } as ListParams,
    page,
    pageSize,
    setValue: (key: string, value: unknown) => patch({ [key]: value }),
    reset: () => setSearchParams(compactParams({ page: 1, page_size: pageSize })),
    setPage: (nextPage: number) => patch({ page: nextPage }, false),
    setPageSize: (nextSize: number) => patch({ page: 1, page_size: nextSize }, false),
  };
}
