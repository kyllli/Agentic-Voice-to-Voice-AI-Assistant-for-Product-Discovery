import { Star, ShoppingCart, Heart } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Product {
  id: string;
  name: string;
  price: number;
  originalPrice?: number;
  rating: number;
  reviews: number;
  image: string;
  category: string;
  inStock: boolean;
}

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
  onFavorite?: (product: Product) => void;
}

const ProductCard = ({ product, onAddToCart, onFavorite }: ProductCardProps) => {
  const discount = product.originalPrice
    ? Math.round(
        ((product.originalPrice - product.price) / product.originalPrice) * 100
      )
    : 0;

  return (
    <div className="group glass rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-elevated hover:scale-[1.02]">
      {/* Image */}
      <div className="relative aspect-square overflow-hidden bg-secondary/50">
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        
        {/* Discount badge */}
        {discount > 0 && (
          <div className="absolute top-3 left-3 px-2 py-1 rounded-full gradient-primary text-xs font-semibold text-primary-foreground">
            -{discount}%
          </div>
        )}

        {/* Favorite button */}
        <button
          onClick={() => onFavorite?.(product)}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-background/80 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-background"
        >
          <Heart className="w-4 h-4 text-foreground" />
        </button>

        {/* Quick add overlay */}
        <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-background/90 to-transparent translate-y-full group-hover:translate-y-0 transition-transform duration-300">
          <button
            onClick={() => onAddToCart?.(product)}
            disabled={!product.inStock}
            className={cn(
              "w-full py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-medium transition-colors",
              product.inStock
                ? "gradient-primary text-primary-foreground hover:opacity-90"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            <ShoppingCart className="w-4 h-4" />
            {product.inStock ? "Add to Cart" : "Out of Stock"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <span className="text-xs text-primary font-medium uppercase tracking-wider">
          {product.category}
        </span>
        <h3 className="text-sm font-semibold text-foreground mt-1 line-clamp-2 group-hover:text-primary transition-colors">
          {product.name}
        </h3>
        
        {/* Rating */}
        <div className="flex items-center gap-1 mt-2">
          <Star className="w-3 h-3 fill-primary text-primary" />
          <span className="text-xs text-foreground font-medium">
            {product.rating.toFixed(1)}
          </span>
          <span className="text-xs text-muted-foreground">
            ({product.reviews.toLocaleString()})
          </span>
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-2 mt-2">
          <span className="text-lg font-bold text-foreground">
            ${product.price.toFixed(2)}
          </span>
          {product.originalPrice && (
            <span className="text-sm text-muted-foreground line-through">
              ${product.originalPrice.toFixed(2)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
