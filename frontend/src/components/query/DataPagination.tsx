import { Button } from "@/components/ui/button";
import { PageSizeSelect } from "@/components/query/PageSizeSelect";

export function DataPagination({ page, pageSize, total, onPageChange, onPageSizeChange }: { page: number; pageSize: number; total: number; onPageChange: (page: number) => void; onPageSizeChange: (pageSize: number) => void }) {
  const pages = total ? Math.ceil(total / pageSize) : 0;
  if (!total) return null;
  const visible = Array.from({ length: Math.min(5, pages) }, (_, index) => Math.max(1, Math.min(pages - 4, page - 2)) + index).filter((item, index, arr) => item <= pages && arr.indexOf(item) === index);
  return (
    <div className="mt-5 flex flex-col justify-between gap-3 text-sm text-stone-500 md:flex-row md:items-center">
      <div>共 {total} 条，第 {page} / {pages} 页</div>
      <div className="flex items-center gap-2">
        <PageSizeSelect value={pageSize} onChange={onPageSizeChange} />
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(1)}>首页</Button>
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>上一页</Button>
        {visible.map((item) => (
          <Button key={item} variant={item === page ? "default" : "secondary"} size="sm" onClick={() => onPageChange(item)}>{item}</Button>
        ))}
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>下一页</Button>
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPageChange(pages)}>末页</Button>
      </div>
    </div>
  );
}
