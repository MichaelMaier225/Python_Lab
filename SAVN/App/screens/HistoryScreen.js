import React, { useContext, useMemo, useState } from "react";
import {
  SafeAreaView,
  StyleSheet,
  Text,
  View,
  FlatList,
  Pressable,
  Modal,
} from "react-native";

import { TransactionsContext } from "../store/TransactionsContext";

const formatCurrency = (value) => `$${value.toFixed(2)}`;

const HistoryScreen = () => {
  const { transactions, removeTransaction } = useContext(TransactionsContext);
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  const sortedTransactions = useMemo(
    () => transactions,
    [transactions]
  );

  const handleConfirm = () => {
    if (selectedTransaction) {
      removeTransaction(selectedTransaction.id);
      setSelectedTransaction(null);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>History</Text>
      <FlatList
        data={sortedTransactions}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>No transactions yet.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View>
              <Text style={styles.itemType}>
                {item.type === "sale" ? "Sale" : "Cost"}
              </Text>
              <Text style={styles.itemDate}>
                {new Date(item.createdAt).toLocaleString()}
              </Text>
            </View>
            <View style={styles.cardRight}>
              <Text style={styles.amount}>{formatCurrency(item.amount)}</Text>
              <Pressable
                style={styles.undoButton}
                onPress={() => setSelectedTransaction(item)}
              >
                <Text style={styles.undoButtonText}>Undo</Text>
              </Pressable>
            </View>
          </View>
        )}
      />
      <Modal
        transparent
        animationType="fade"
        visible={Boolean(selectedTransaction)}
        onRequestClose={() => setSelectedTransaction(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Undo transaction?</Text>
            <Text style={styles.modalBody}>
              This will remove the transaction and update totals.
            </Text>
            <View style={styles.modalActions}>
              <Pressable
                style={styles.modalButton}
                onPress={() => setSelectedTransaction(null)}
              >
                <Text style={styles.modalButtonText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[styles.modalButton, styles.modalButtonPrimary]}
                onPress={handleConfirm}
              >
                <Text style={styles.modalButtonTextPrimary}>Undo</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6F7FB",
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    color: "#101828",
    marginBottom: 12,
  },
  listContent: {
    paddingBottom: 32,
    gap: 12,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    shadowColor: "#101828",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  itemType: {
    fontSize: 18,
    fontWeight: "600",
    color: "#101828",
    marginBottom: 4,
  },
  itemDate: {
    fontSize: 12,
    color: "#667085",
  },
  cardRight: {
    alignItems: "flex-end",
  },
  amount: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1B6EF3",
    marginBottom: 8,
  },
  undoButton: {
    minHeight: 48,
    minWidth: 80,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#F04438",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  undoButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#F04438",
  },
  emptyState: {
    alignItems: "center",
    marginTop: 48,
  },
  emptyText: {
    fontSize: 16,
    color: "#667085",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(16, 24, 40, 0.5)",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    width: "100%",
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#101828",
    marginBottom: 8,
  },
  modalBody: {
    fontSize: 14,
    color: "#667085",
    marginBottom: 20,
  },
  modalActions: {
    flexDirection: "row",
    gap: 12,
  },
  modalButton: {
    flex: 1,
    minHeight: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#D0D5DD",
    alignItems: "center",
    justifyContent: "center",
  },
  modalButtonPrimary: {
    backgroundColor: "#F04438",
    borderColor: "#F04438",
  },
  modalButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#101828",
  },
  modalButtonTextPrimary: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FFFFFF",
  },
});

export default HistoryScreen;
