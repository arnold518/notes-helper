import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

interface Props {
  excerpt: string;
}

export default function ExcerptPreview({ excerpt }: Props) {
  if (!excerpt.trim()) {
    return (
      <div className="excerpt-preview-empty">
        No excerpt yet. Run Match to populate.
      </div>
    );
  }

  const blocks = excerpt.split(/\n\s*---\s*\n/);

  return (
    <div className="excerpt-preview">
      {blocks.map((block, i) => {
        const headerMatch = block.match(/^\[([^\]]+)\]\s*\n([\s\S]*)/);
        const header = headerMatch ? headerMatch[1] : null;
        const content = headerMatch ? headerMatch[2].trim() : block.trim();
        return (
          <div key={i} className="excerpt-block">
            {header && <div className="excerpt-block-header">{header}</div>}
            <div className="excerpt-block-text">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
