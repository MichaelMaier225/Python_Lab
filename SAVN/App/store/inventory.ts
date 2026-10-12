import { create } from "zustand";
import { nanoid } from "nanoid";

export type Product = {
  id: string;
  name: string;
  qty: number;
};

type UndoAction =
  | { type: "add"; product: Product }
  | { type: "sell"; productId: string; qty: number }
  | { type: "restock"; productId: string; qty: number }
  | { type: "adjust"; productId: string; previousQty: number };

type InventoryStore = {
  products: Product[];
  undoStack: UndoAction[];

  addProduct: (name: string, qty: number) => void;
  sellProduct: (id: string, qty: number) => void;
  restockProduct: (id: string, qty: number) => void;
  adjustProduct: (id: string, newQty: number) => void;

  undoLastAction: () => void;
};

export const useInventoryStore = create<InventoryStore>((set, get) => ({
  products: [],
  undoStack: [],

  addProduct: (name, qty) => {
    const product: Product = {
      id: nanoid(),
      name,
      qty,
    };

    set((state) => ({
      products: [...state.products, product],
      undoStack: [...state.undoStack, { type: "add", product }],
    }));
  },

  sellProduct: (id, qty) => {
    set((state) => {
      const product = state.products.find((p) => p.id === id);
      if (!product || product.qty < qty) return state;

      return {
        products: state.products.map((p) =>
          p.id === id ? { ...p, qty: p.qty - qty } : p
        ),
        undoStack: [
          ...state.undoStack,
          { type: "sell", productId: id, qty },
        ],
      };
    });
  },

  restockProduct: (id, qty) => {
    set((state) => {
      const product = state.products.find((p) => p.id === id);
      if (!product) return state;

      return {
        products: state.products.map((p) =>
          p.id === id ? { ...p, qty: p.qty + qty } : p
        ),
        undoStack: [
          ...state.undoStack,
          { type: "restock", productId: id, qty },
        ],
      };
    });
  },

  adjustProduct: (id, newQty) => {
    set((state) => {
      const product = state.products.find((p) => p.id === id);
      if (!product) return state;

      return {
        products: state.products.map((p) =>
          p.id === id ? { ...p, qty: newQty } : p
        ),
        undoStack: [
          ...state.undoStack,
          {
            type: "adjust",
            productId: id,
            previousQty: product.qty,
          },
        ],
      };
    });
  },

  undoLastAction: () => {
    const stack = get().undoStack;
    if (stack.length === 0) return;

    const last = stack[stack.length - 1];

    set((state) => {
      let products = [...state.products];

      switch (last.type) {
        case "add":
          products = products.filter((p) => p.id !== last.product.id);
          break;

        case "sell":
          products = products.map((p) =>
            p.id === last.productId
              ? { ...p, qty: p.qty + last.qty }
              : p
          );
          break;

        case "restock":
          products = products.map((p) =>
            p.id === last.productId
              ? { ...p, qty: p.qty - last.qty }
              : p
          );
          break;

        case "adjust":
          products = products.map((p) =>
            p.id === last.productId
              ? { ...p, qty: last.previousQty }
              : p
          );
          break;
      }

      return {
        products,
        undoStack: state.undoStack.slice(0, -1),
      };
    });
  },
}));
