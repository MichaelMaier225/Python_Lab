import React, { createContext, useMemo, useState } from "react";

export const TransactionsContext = createContext({
  transactions: [],
  totals: {
    sales: 0,
    costs: 0,
    net: 0,
  },
  addTransaction: () => {},
  removeTransaction: () => {},
});

const calculateTotals = (transactions) => {
  return transactions.reduce(
    (acc, transaction) => {
      if (transaction.type === "sale") {
        acc.sales += transaction.amount;
      } else {
        acc.costs += transaction.amount;
      }
      acc.net = acc.sales - acc.costs;
      return acc;
    },
    { sales: 0, costs: 0, net: 0 }
  );
};

export const TransactionsProvider = ({ children }) => {
  const [transactions, setTransactions] = useState([]);

  const addTransaction = ({ amount, type }) => {
    setTransactions((prev) => [
      {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        amount,
        type,
        createdAt: new Date().toISOString(),
      },
      ...prev,
    ]);
  };

  const removeTransaction = (transactionId) => {
    setTransactions((prev) => prev.filter((entry) => entry.id !== transactionId));
  };

  const totals = useMemo(() => calculateTotals(transactions), [transactions]);

  const value = useMemo(
    () => ({
      transactions,
      totals,
      addTransaction,
      removeTransaction,
    }),
    [transactions, totals]
  );

  return (
    <TransactionsContext.Provider value={value}>
      {children}
    </TransactionsContext.Provider>
  );
};
