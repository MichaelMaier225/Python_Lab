import { useLocalSearchParams, router } from "expo-router"
import { useEffect, useState } from "react"
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
} from "react-native"

import {
  getProducts,
  updateProduct,
  removeProduct,
  setProductInventory,
  Product,
} from "../../store/products"
import { BrandColors } from "../../constants/brand"

export default function ProductEditScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const productId = Number(id)

  const [product, setProduct] = useState<Product | null>(null)

  const [name, setName] = useState("")
  const [price, setPrice] = useState("")
  const [cost, setCost] = useState("")
  const [inventory, setInventory] = useState("")

  useEffect(() => {
    const found = getProducts().find(p => p.id === productId)
    if (found) {
      setProduct(found)
      setName(found.name)
      setPrice(String(found.price))
      setCost(String(found.cost))
      setInventory(String(found.qty))
    }
  }, [])

  if (!product) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.title}>Product not found</Text>
        </View>
      </SafeAreaView>
    )
  }

  const handleSave = () => {
    if (!name || !price || !cost) return

    updateProduct(product.id, {
      name,
      price: Number(price),
      cost: Number(cost),
    })

    router.back()
  }

  const handleInventoryUpdate = () => {
    if (!inventory) return

    const inventoryValue = Number.parseInt(inventory, 10)

    if (Number.isNaN(inventoryValue) || inventoryValue < 0) {
      Alert.alert(
        "Invalid inventory",
        "Enter a valid inventory count."
      )
      return
    }

    setProductInventory(product.id, inventoryValue)
    router.back()
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Edit Product</Text>

        <Text style={styles.label}>Product name</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
        />

        <Text style={styles.label}>Price per unit</Text>
        <TextInput
          style={styles.input}
          value={price}
          keyboardType="numeric"
          onChangeText={setPrice}
        />

        <Text style={styles.label}>Cost per unit</Text>
        <TextInput
          style={styles.input}
          value={cost}
          keyboardType="numeric"
          onChangeText={setCost}
        />

        <Text style={styles.label}>Inventory on hand</Text>
        <TextInput
          style={styles.input}
          value={inventory}
          keyboardType="numeric"
          onChangeText={setInventory}
        />
        <Text style={styles.helper}>
          Adjusting inventory does not change revenue or expenses.
        </Text>
        <TouchableOpacity
          style={styles.inventoryBtn}
          onPress={handleInventoryUpdate}
        >
          <Text style={styles.inventoryText}>Update inventory</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.saveBtn}
          onPress={handleSave}
        >
          <Text style={styles.saveText}>Save changes</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.deleteBtn}
          onPress={() =>
            Alert.alert(
              "Archive product",
              "This hides this product without changing revenue or expenses.",
              [
                { text: "Cancel", style: "cancel" },
                {
                  text: "Archive",
                  style: "destructive",
                  onPress: () => {
                    removeProduct(product.id)
                    router.back()
                  },
                },
              ]
            )
          }
        >
          <Text style={styles.deleteText}>Archive product</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: BrandColors.pageBackground,
  },
  container: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 20,
    color: BrandColors.headerBackground,
  },
  label: {
    fontSize: 14,
    marginBottom: 6,
    color: BrandColors.textSecondary,
  },
  input: {
    borderWidth: 1,
    borderColor: BrandColors.cardBorder,
    borderRadius: 12,
    padding: 12,
    marginBottom: 15,
    backgroundColor: BrandColors.card,
    color: BrandColors.textPrimary,
  },
  helper: {
    fontSize: 12,
    color: BrandColors.textSecondary,
    marginBottom: 12,
  },
  inventoryBtn: {
    backgroundColor: BrandColors.accent,
    padding: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 20,
  },
  inventoryText: {
    color: BrandColors.textOnBrand,
    fontWeight: "bold",
  },
  saveBtn: {
    backgroundColor: BrandColors.accent,
    padding: 15,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 10,
  },
  saveText: {
    color: BrandColors.textOnBrand,
    fontWeight: "bold",
  },
  deleteBtn: {
    marginTop: 30,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: BrandColors.accent,
    alignItems: "center",
    backgroundColor: BrandColors.accentSoft,
  },
  deleteText: {
    color: BrandColors.accentDark,
    fontWeight: "bold",
  },
})
