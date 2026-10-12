import React from "react";
import { SafeAreaView, StyleSheet, Text, View, Pressable } from "react-native";

const MoreScreen = () => {
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>More</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Settings</Text>
        <View style={styles.card}>
          <Text style={styles.itemText}>Notifications</Text>
          <Text style={styles.itemSubtext}>Manage reminders and alerts</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.itemText}>Currency</Text>
          <Text style={styles.itemSubtext}>USD - United States Dollar</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Export</Text>
        <View style={styles.card}>
          <Text style={styles.itemText}>Export CSV</Text>
          <Text style={styles.itemSubtext}>Save a copy of your transactions</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.itemText}>Share Summary</Text>
          <Text style={styles.itemSubtext}>Send today&apos;s totals</Text>
        </View>
      </View>

      <Pressable style={styles.logoutButton} onPress={() => {}}>
        <Text style={styles.logoutText}>Logout</Text>
      </Pressable>

      <View style={styles.aboutSection}>
        <Text style={styles.sectionTitle}>About</Text>
        <Text style={styles.aboutText}>
          ClearLedger helps you track daily sales and costs with a simple, reliable
          workflow.
        </Text>
      </View>
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
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#101828",
    marginBottom: 8,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    minHeight: 56,
    justifyContent: "center",
  },
  itemText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#101828",
  },
  itemSubtext: {
    fontSize: 12,
    color: "#667085",
    marginTop: 4,
  },
  logoutButton: {
    backgroundColor: "#F04438",
    borderRadius: 16,
    minHeight: 56,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  aboutSection: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
  },
  aboutText: {
    fontSize: 13,
    color: "#667085",
    lineHeight: 18,
  },
});

export default MoreScreen;
