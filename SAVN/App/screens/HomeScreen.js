import React, { useContext, useMemo } from "react";
import {
  SafeAreaView,
  StyleSheet,
  Text,
  View,
  Pressable,
  ScrollView,
} from "react-native";
import { useNavigation } from "@react-navigation/native";

import { TransactionsContext } from "../store/TransactionsContext";

const formatCurrency = (value) => `$${value.toFixed(2)}`;

const isToday = (isoDate) => {
  const date = new Date(isoDate);
  const today = new Date();
  return date.toDateString() === today.toDateString();
};

const HomeScreen = () => {
  const navigation = useNavigation();
  const { transactions } = useContext(TransactionsContext);

  const todayStats = useMemo(() => {
    const todaysTransactions = transactions.filter((transaction) =>
      isToday(transaction.createdAt)
    );
    const sales = todaysTransactions.filter((transaction) => transaction.type === "sale");
    const costs = todaysTransactions.filter((transaction) => transaction.type === "cost");
    const salesTotal = sales.reduce((acc, transaction) => acc + transaction.amount, 0);
    const costsTotal = costs.reduce((acc, transaction) => acc + transaction.amount, 0);
    const net = salesTotal - costsTotal;
    return {
      salesTotal,
      costsTotal,
      net,
      salesCount: sales.length,
      costsCount: costs.length,
      averageSale: sales.length ? salesTotal / sales.length : 0,
    };
  }, [transactions]);

  const menuItems = useMemo(() => {
    const fallbackItems = [
      { name: "Pork Sandwich", price: 5.8 },
      { name: "Pho Beef Noodle", price: 6.3 },
      { name: "Spicy Goun Fresh Spring", price: 4.5 },
      { name: "Iced Coffee", price: 2.4 },
    ];

    if (!transactions.length) {
      return fallbackItems;
    }

    return transactions.slice(0, 4).map((transaction, index) => ({
      name: transaction.description || `Item ${index + 1}`,
      price: transaction.amount,
    }));
  }, [transactions]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.brand}>SAVN</Text>
        <Text style={styles.settingsIcon}>⚙</Text>
      </View>

      <View style={styles.segmentedControl}>
        <View style={[styles.segment, styles.segmentActive]}>
          <Text style={styles.segmentTextActive}>Executive</Text>
        </View>
        <View style={styles.segment}>
          <Text style={styles.segmentText}>Analytics</Text>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.cardRow}>
          <View style={[styles.statCard, styles.statCardPrimary]}>
            <Text style={styles.statLabel}>Revenue</Text>
            <Text style={styles.statValue}>{formatCurrency(todayStats.salesTotal)}</Text>
            <Text style={styles.statMeta}>Revenue: {todayStats.salesCount}</Text>
            <Text style={styles.statMeta}>
              Avg {formatCurrency(todayStats.averageSale)}
            </Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Today</Text>
            <Text style={styles.statValue}>{formatCurrency(todayStats.net)}</Text>
            <Text style={styles.statMeta}>Expense: {todayStats.costsCount}</Text>
            <Text style={styles.statMeta}>Avg {formatCurrency(todayStats.costsTotal)}</Text>
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Menu</Text>
          <Text style={styles.sectionSubtitle}>Popular Today</Text>
        </View>

        <View style={styles.menuCard}>
          {menuItems.map((item) => (
            <View key={item.name} style={styles.menuRow}>
              <View>
                <Text style={styles.menuName}>{item.name}</Text>
                <Text style={styles.menuPrice}>{formatCurrency(item.price)}</Text>
              </View>
              <View style={styles.menuActions}>
                <Pressable style={[styles.actionButton, styles.actionButtonDark]}>
                  <Text style={[styles.actionButtonText, styles.actionButtonTextLight]}>-</Text>
                </Pressable>
                <Pressable style={styles.actionButton}>
                  <Text style={styles.actionButtonText}>+</Text>
                </Pressable>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.actions}>
          <Pressable
            style={styles.primaryButton}
            onPress={() => navigation.navigate("Add", { type: "sale" })}
          >
            <Text style={styles.primaryButtonText}>Add Sale</Text>
          </Pressable>
          <Pressable
            style={[styles.primaryButton, styles.secondaryButton]}
            onPress={() => navigation.navigate("Add", { type: "cost" })}
          >
            <Text style={styles.primaryButtonText}>Add Cost</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6F3F4",
  },
  header: {
    backgroundColor: "#C21F2B",
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brand: {
    fontSize: 24,
    fontWeight: "800",
    color: "#FFFFFF",
    letterSpacing: 0.8,
  },
  settingsIcon: {
    fontSize: 20,
    color: "#FFFFFF",
  },
  segmentedControl: {
    flexDirection: "row",
    backgroundColor: "#E9E2E4",
    marginHorizontal: 20,
    marginTop: -16,
    borderRadius: 18,
    padding: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 14,
  },
  segmentActive: {
    backgroundColor: "#FFFFFF",
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  segmentText: {
    fontSize: 14,
    color: "#8E7B80",
    fontWeight: "600",
  },
  segmentTextActive: {
    fontSize: 14,
    color: "#C21F2B",
    fontWeight: "700",
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 32,
  },
  cardRow: {
    flexDirection: "row",
    gap: 14,
    marginBottom: 22,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 16,
    shadowColor: "#1F2937",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 8 },
    elevation: 2,
  },
  statCardPrimary: {
    borderWidth: 1,
    borderColor: "#F3D5D8",
  },
  statLabel: {
    fontSize: 14,
    color: "#A33A45",
    fontWeight: "700",
    marginBottom: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: "800",
    color: "#1F2937",
    marginBottom: 8,
  },
  statMeta: {
    fontSize: 12,
    color: "#8E7B80",
  },
  sectionHeader: {
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F2937",
  },
  sectionSubtitle: {
    fontSize: 14,
    color: "#8E7B80",
    marginTop: 2,
  },
  menuCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 22,
    paddingVertical: 10,
    paddingHorizontal: 12,
    shadowColor: "#1F2937",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  menuRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#F1E7E9",
  },
  menuName: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F2937",
  },
  menuPrice: {
    fontSize: 13,
    color: "#A33A45",
    marginTop: 4,
  },
  menuActions: {
    flexDirection: "row",
    gap: 8,
  },
  actionButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#F7F0F1",
    alignItems: "center",
    justifyContent: "center",
  },
  actionButtonDark: {
    backgroundColor: "#1F2937",
  },
  actionButtonText: {
    color: "#C21F2B",
    fontSize: 16,
    fontWeight: "700",
  },
  actionButtonTextLight: {
    color: "#FFFFFF",
  },
  actions: {
    marginTop: 24,
    gap: 14,
  },
  primaryButton: {
    backgroundColor: "#C21F2B",
    borderRadius: 16,
    minHeight: 54,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryButton: {
    backgroundColor: "#1F2937",
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFFFFF",
  },
});

export default HomeScreen;
