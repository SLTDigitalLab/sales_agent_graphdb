import React from 'react';
import './ProductCanvas.css';

const ProductCanvas = ({ product, isLoading }) => {

    // --- HELPER: Smart Text Cleaner ---
    const cleanDescription = (text) => {
        if (!text || text === "No description available.") return [];

        let cleanText = text;

        // 1. Fix "glued" words (lowercase/number followed immediately by Uppercase)
        // Example: "10mMaximum" -> "10m Maximum", "RecordingBuilt" -> "Recording Built"
        cleanText = cleanText.replace(/([a-z0-9])([A-Z])/g, '$1 $2');

        // 2. Fix missing space after colon
        // Example: "Overview:Effective" -> "Overview: Effective"
        cleanText = cleanText.replace(/(:)([A-Z])/g, '$1 $2');

        // 3. Identify common headers to force new lines
        // We replace specific keywords with a unique delimiter "|" to split them later
        const keywords = [
            "Overview:", "Effective Vision", "Maximum Image", "Snapshot",
            "Built-in", "Rotate", "Tilt", "Email", "Micro SD", "Not compatible"
        ];

        keywords.forEach(keyword => {
            // Look for the keyword and put a delimiter "|" before it
            const regex = new RegExp(keyword, 'g');
            cleanText = cleanText.replace(regex, `|${keyword}`);
        });

        // 4. Split by the delimiter and filter empty lines
        return cleanText.split('|').filter(line => line.trim().length > 0);
    };

    const descriptionPoints = product ? cleanDescription(product.description) : [];

    // 1. Empty State
    if (!product && !isLoading) {
        return (
            <div className="canvas-container empty">
                <div className="empty-state-content">
                    <span className="icon">🛍️</span>
                    <h3>Product Details</h3>
                    <p>Ask the agent about a product to see details here.</p>
                </div>
            </div>
        );
    }

    // 2. Loading State
    if (isLoading) {
        return (
            <div className="canvas-container loading">
                <div className="spinner"></div>
                <p>Fetching product details...</p>
            </div>
        );
    }

    // 3. Active Product State
    return (
        <div className="canvas-container active">
            <div className="canvas-header">
                <span className={`status-badge ${product.stock > 0 ? 'in-stock' : 'out-of-stock'}`}>
                    {product.stock > 0 ? 'In Stock' : 'Out of Stock'}
                </span>
                {product.stock > 0 && <span className="stock-count">{product.stock} units</span>}
            </div>

            <div className="product-image-wrapper">
                <img
                    src={product.image || "https://via.placeholder.com/300?text=No+Image"}
                    alt={product.name}
                    className="product-image"
                    onError={(e) => { e.target.src = "https://via.placeholder.com/300?text=Image+Not+Found"; }}
                />
            </div>

            <div className="product-info">
                <h2 className="product-title">{product.name}</h2>
                <h3 className="product-price">Rs. {product.price.toLocaleString()}</h3>

                <div className="product-specs">
                    <h4>Description</h4>
                    {/* RENDER CLEANED LIST */}
                    <ul className="description-list">
                        {descriptionPoints.map((point, index) => (
                            <li key={index}>{point.trim()}</li>
                        ))}
                    </ul>
                </div>

                {/* Specs List */}
                {product.specs && (
                    <div className="specs-list">
                        {Object.entries(product.specs).map(([key, value]) => (
                            <div key={key} className="spec-item">
                                <span className="spec-label">{key}:</span>
                                <span className="spec-value">{value}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ProductCanvas;