import React, { useContext, useEffect, useMemo, useState } from "react";
import {
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
  Pressable,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";

import { TransactionsContext } from "../store/TransactionsContext";

const AddScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { addTransaction } = useContext(TransactionsContext);
  const [amount, setAmount] = useState("");
  const [type, setType] = useState("sale");

  useEffect(() => {
    if (route.params?.type) {
      setType(route.params.type);
    }
  }, [route.params]);

  const parsedAmount = useMemo(() => Number.parseFloat(amount), [amount]);
  const isValid = Number.isFinite(parsedAmount) && parsedAmount > 0;

  const handleSave = () => {
    if (!isValid) {
      return;
    }
    addTransaction({ amount: parsedAmount, type });
    setAmount("");
    navigation.navigate("Home");
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <Text style={styles.title}>Add Transaction</Text>
        <View style={styles.card}>
          <Text style={styles.label}>Amount</Text>
          <TextInput
            style={styles.input}
            placeholder="$0.00"
            keyboardType="decimal-pad"
            value={amount}
            onChangeText={setAmount}
          />
          <Text style={styles.label}>Type</Text>
          <View style={styles.typeRow}>
            <Pressable
              style={[
                styles.typeButton,
                type === "sale" && styles.typeButtonActive,
              ]}
              onPress={() => setType("sale")}
            >
              <Text
                style={[
                  styles.typeButtonText,
                  type === "sale" && styles.typeButtonTextActive,
                ]}
              >
                Sale
              </Text>
            </Pressable>
            <Pressable
              style={[
                styles.typeButton,
                type === "cost" && styles.typeButtonActive,
              ]}
              onPress={() => setType("cost")}
            >
              <Text
                style={[
                  styles.typeButtonText,
                  type === "cost" && styles.typeButtonTextActive,
                ]}
              >
                Cost
              </Text>
            </Pressable>
          </View>
        </View>
        <Pressable
          style={[styles.saveButton, !isValid && styles.saveButtonDisabled]}
          onPress={handleSave}
        >
          <Text style={styles.saveButtonText}>Save</Text>
        </Pressable>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6F7FB",
    paddingHorizontal: 20,
  },
  keyboardView: {
    flex: 1,
    paddingTop: 16,
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    color: "#101828",
    marginBottom: 16,
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    shadowColor: "#101828",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: "#667085",
    marginBottom: 8,
  },
  input: {
    backgroundColor: "#F1F4F9",
    borderRadius: 12,
    minHeight: 52,
    paddingHorizontal: 16,
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 16,
  },
  typeRow: {
    flexDirection: "row",
    gap: 12,
  },
  typeButton: {
    flex: 1,
    minHeight: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#D0D5DD",
    alignItems: "center",
    justifyContent: "center",
  },
  typeButtonActive: {
    backgroundColor: "#1B6EF3",
    borderColor: "#1B6EF3",
  },
  typeButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#101828",
  },
  typeButtonTextActive: {
    color: "#FFFFFF",
  },
  saveButton: {
    backgroundColor: "#12B76A",
    borderRadius: 16,
    minHeight: 56,
    alignItems: "center",
    justifyContent: "center",
  },
  saveButtonDisabled: {
    opacity: 0.5,
  },
  saveButtonText: {
    fontSize: 18,
    fontWeight: "700",
    color: "#FFFFFF",
  },
});

export default AddScreen;
