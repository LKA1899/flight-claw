export function MarkdownView({ content }: { content?: string | null }) {
  if (!content) return <div className="text-sm text-stone-500">报告内容为空。</div>;
  const lines = content.split("\n");
  return (
    <article className="prose prose-stone max-w-none">
      {lines.map((line, index) => {
        if (line.startsWith("### ")) return <h3 key={index} className="mt-6 text-lg font-semibold">{line.slice(4)}</h3>;
        if (line.startsWith("## ")) return <h2 key={index} className="mt-8 text-xl font-semibold">{line.slice(3)}</h2>;
        if (line.startsWith("# ")) return <h1 key={index} className="text-3xl font-semibold">{line.slice(2)}</h1>;
        if (line.startsWith("- ")) return <li key={index} className="ml-5 list-disc text-sm leading-7">{line.slice(2)}</li>;
        if (!line.trim()) return <div key={index} className="h-3" />;
        return <p key={index} className="text-sm leading-7 text-stone-700">{line}</p>;
      })}
    </article>
  );
}
