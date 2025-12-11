import { Star, ExternalLink, FileText } from "lucide-react";

export interface ComparisonProduct {
  id: string;
  name: string;
  brand: string;
  price: number;
  rating: number;
  reviews: number;
  ingredients: string;
  sourceType: "doc" | "link";
  sourceLabel: string;
  sourceUrl?: string;
  isTopPick?: boolean;
  imageUrl?: string;
}

interface ProductComparisonTableProps {
  products: ComparisonProduct[];
  onSelectProduct?: (product: ComparisonProduct) => void;
}

const ProductComparisonTable = ({ products, onSelectProduct }: ProductComparisonTableProps) => {
  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border/50">
              <th className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3">
                Product
              </th>
              <th className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3">
                Price
              </th>
              <th className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3">
                Rating
              </th>
              <th className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3">
                Source
              </th>
            </tr>
          </thead>
          <tbody>
            {products.map((product, index) => (
              <tr
                key={product.id}
                onClick={() => onSelectProduct?.(product)}
                className={`
                  border-b border-border/30 last:border-b-0 transition-colors cursor-pointer
                  ${product.isTopPick ? "bg-primary/10" : "hover:bg-secondary/50"}
                `}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    {product.imageUrl && (
                      <img
                        src={product.imageUrl}
                        alt={product.name}
                        className="w-12 h-12 object-cover rounded-lg bg-secondary"
                      />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">
                          {product.name}
                        </p>
                        {product.isTopPick && (
                          <span className="px-2 py-0.5 rounded-full gradient-primary text-[10px] font-bold text-primary-foreground uppercase">
                            Top Pick
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{product.brand}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className="text-sm font-bold text-foreground">
                    ${product.price.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-1">
                    <Star className="w-3.5 h-3.5 fill-primary text-primary" />
                    <span className="text-sm font-medium text-foreground">
                      {product.rating.toFixed(1)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      ({product.reviews.toLocaleString()})
                    </span>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <a
                    href={product.sourceUrl || "#"}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                  >
                    {product.sourceType === "doc" ? (
                      <FileText className="w-3.5 h-3.5" />
                    ) : (
                      <ExternalLink className="w-3.5 h-3.5" />
                    )}
                    {product.sourceLabel}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ProductComparisonTable;
