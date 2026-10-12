import { useCallback, useEffect, useMemo, useState } from "react"

import {
  getLanguage,
  setLanguage,
  subscribeToLanguage,
  Language,
} from "../store/settings"

type TranslationKey =
  | "analytics"
  | "analyticsTitle"
  | "appLanguage"
  | "avgSale"
  | "bestMarginItem"
  | "bulkSale"
  | "bulkRestock"
  | "businessHealth"
  | "cancel"
  | "changeLanguageHelper"
  | "clear"
  | "clearHistory"
  | "clearHistoryHelper"
  | "clearHistoryWarningTitle"
  | "clearHistoryWarningBody"
  | "currency"
  | "currencyHelper"
  | "daysTracked"
  | "enterQuantity"
  | "enterValidQuantityTitle"
  | "enterValidQuantityBody"
  | "enterValidTotalTitle"
  | "enterValidTotalBody"
  | "expenses"
  | "estimatedTotal"
  | "explore"
  | "exploreHeadline"
  | "exploreFastSalesTitle"
  | "exploreFastSalesBody"
  | "exploreBulkSalesTitle"
  | "exploreBulkSalesBody"
  | "exploreBulkRestockTitle"
  | "exploreBulkRestockBody"
  | "exploreCatalogTitle"
  | "exploreCatalogBody"
  | "exploreUndoTitle"
  | "exploreUndoBody"
  | "exploreInsightsTitle"
  | "exploreInsightsBody"
  | "exploreHistoryTitle"
  | "exploreHistoryBody"
  | "exploreAnalyticsTitle"
  | "exploreAnalyticsBody"
  | "exploreSettingsTitle"
  | "exploreSettingsBody"
  | "grossMargin"
  | "grossProfit"
  | "history"
  | "historyTitle"
  | "historyEmpty"
  | "historySale"
  | "historyRestock"
  | "historyAdjustment"
  | "holdRestock"
  | "hourly"
  | "insufficientStockTitle"
  | "insufficientStockBody"
  | "inventory"
  | "inventoryValue"
  | "inventoryWatch"
  | "insights"
  | "insightsTitle"
  | "lifetimeRevenue"
  | "language"
  | "lowStock"
  | "monthly"
  | "yearly"
  | "allTime"
  | "mostRestockedItem"
  | "mostSoldItem"
  | "apply"
  | "periodMonth"
  | "periodToday"
  | "periodWeek"
  | "periodYear"
  | "potentialRevenue"
  | "noRestocks"
  | "noSales"
  | "quantity"
  | "restock"
  | "restockSpend"
  | "reportRange"
  | "sales"
  | "salesTrend"
  | "salesLogged"
  | "profit"
  | "productBreakdown"
  | "totalProducts"
  | "productInsights"
  | "qtyUnitCost"
  | "qtyUnitPrice"
  | "revenue"
  | "restocked"
  | "sold"
  | "salesOverview"
  | "settings"
  | "settingsTitle"
  | "moreTools"
  | "moreToolsHelper"
  | "moreAnalyticsHelper"
  | "moreInsightsHelper"
  | "moreExploreHelper"
  | "slowMover"
  | "stockHealthy"
  | "topRevenueItem"
  | "totalCost"
  | "totalRevenue"
  | "totalSales"
  | "undo"
  | "undoTransactionTitle"
  | "undoTransactionBody"
  | "vendors"
  | "weekly"
  | "daily"
  | "revenueVsRestock"
  | "currencyUSD"
  | "currencyVND"
  | "activeItems"
  | "activate"
  | "activeProducts"
  | "addToCatalog"
  | "archive"
  | "archiveProductBody"
  | "archiveProductTitle"
  | "catalogHelper"
  | "costPerUnit"
  | "deactivate"
  | "edit"
  | "inactiveProducts"
  | "invalidCostBody"
  | "invalidCostTitle"
  | "invalidInventoryBody"
  | "invalidInventoryTitle"
  | "invalidPriceBody"
  | "invalidPriceTitle"
  | "inventoryHint"
  | "inventoryOnHand"
  | "missingNameBody"
  | "missingNameTitle"
  | "newProduct"
  | "noActiveProducts"
  | "noInactiveProducts"
  | "onHand"
  | "pricePerUnit"
  | "productName"
  | "save"
  | "searchProducts"
  | "searchPlaceholder"
  | "searchResultsEmpty"
  | "emptyInventoryTitle"
  | "emptyInventoryBody"
  | "emptyInventoryCta"
  | "updateProduct"
  | "vendorCatalogSubtitle"
  | "vendorCatalogTitle"
  | "left"

const translations: Record<Language, Record<TranslationKey, string>> = {
  en: {
    analytics: "Analytics",
    analyticsTitle: "Analytics",
    appLanguage: "App language",
    avgSale: "Avg sale",
    bestMarginItem: "Best margin item",
    bulkSale: "Bulk sale",
    bulkRestock: "Bulk restock",
    businessHealth: "Business health",
    cancel: "Cancel",
    changeLanguageHelper:
      "Switch languages for labels across the app.",
    clear: "Clear",
    clearHistory: "Clear history",
    clearHistoryHelper:
      "Select a range to remove history entries and update revenue and expenses totals.",
    clearHistoryWarningTitle: "Clear history?",
    clearHistoryWarningBody:
      "This will remove matching history entries and adjust revenue and expenses.",
    currency: "Currency",
    currencyHelper: "Choose the currency symbol for prices.",
    daysTracked: "Days tracked",
    enterQuantity: "Enter quantity",
    enterValidQuantityTitle: "Enter a valid quantity",
    enterValidQuantityBody: "Quantity must be at least 1.",
    enterValidTotalTitle: "Enter a valid total cost",
    enterValidTotalBody: "Total cost must be 0 or more.",
    expenses: "Expenses",
    estimatedTotal: "Estimated total",
    explore: "Explore",
    exploreHeadline: "Quick tips for busy vendor days.",
    exploreFastSalesTitle: "Sell fast from the Inventory tab",
    exploreFastSalesBody:
      "Tap − or + to record sales and restocks in seconds. Each tap updates stock and revenue automatically.",
    exploreBulkSalesTitle: "Long-press − for bulk sales",
    exploreBulkSalesBody:
      "Selling a lot at once? Long-press − to enter quantity and total revenue, including discounts.",
    exploreBulkRestockTitle: "Long-press + for bulk restock",
    exploreBulkRestockBody:
      "When you restock a lot at once, long-press + to enter quantity and total cost in one step.",
    exploreCatalogTitle: "Keep your catalog updated",
    exploreCatalogBody:
      "Search products, update prices and costs, adjust inventory, and archive items without losing history.",
    exploreUndoTitle: "Undo the last action",
    exploreUndoBody:
      "Made a mistake? Tap Undo to reverse the most recent sale or restock.",
    exploreInsightsTitle: "Spot trends with Insights",
    exploreInsightsBody:
      "See revenue vs restock spend, sales trends, and product performance across report ranges.",
    exploreHistoryTitle: "Track every sale",
    exploreHistoryBody:
      "History keeps a log of sales, restocks, and adjustments so you can review busy periods quickly.",
    exploreAnalyticsTitle: "Know your best sellers",
    exploreAnalyticsBody:
      "Analytics shows top items, revenue, and low stock so you know what to restock first.",
    exploreSettingsTitle: "Personalize your settings",
    exploreSettingsBody:
      "Switch language, set your currency, and clear history when you need a fresh start.",
    grossMargin: "Gross margin",
    grossProfit: "Gross profit",
    history: "History",
    historyTitle: "History",
    historyEmpty: "No activity yet. Sales and restocks will show here.",
    historySale: "Sold {quantity} {product} · {amount}",
    historyRestock: "Restocked {quantity} {product} · {amount}",
    historyAdjustment: "Adjusted {quantity} {product} · {amount}",
    holdRestock: "Hold + to restock in bulk. Hold − to sell in bulk.",
    hourly: "Hourly",
    insufficientStockTitle: "Not enough inventory",
    insufficientStockBody:
      "You cannot sell more than the available stock.",
    inventory: "Inventory",
    inventoryValue: "Inventory value",
    inventoryWatch: "Inventory watch",
    insights: "Insights",
    insightsTitle: "Insights",
    lifetimeRevenue: "Lifetime revenue",
    language: "Language",
    lowStock: "Low stock",
    monthly: "Monthly",
    yearly: "Yearly",
    allTime: "All time",
    mostRestockedItem: "Most restocked item",
    mostSoldItem: "Most sold item",
    apply: "Apply",
    periodMonth: "This Month",
    periodToday: "Today",
    periodWeek: "This Week",
    periodYear: "This Year",
    potentialRevenue: "Potential revenue",
    noRestocks: "No restocks yet",
    noSales: "No sales yet",
    quantity: "Quantity",
    restock: "Restock",
    restockSpend: "Restock spend",
    reportRange: "Report range",
    sales: "Sales",
    salesTrend: "Sales trend",
    salesLogged: "total sales logged.",
    profit: "Profit",
    productBreakdown: "Product breakdown",
    totalProducts: "Total products",
    productInsights: "Product insights",
    qtyUnitCost: "qty × unit cost",
    qtyUnitPrice: "qty × unit price",
    revenue: "Revenue",
    restocked: "restocked",
    sold: "sold",
    salesOverview: "Sales overview",
    settings: "Settings",
    settingsTitle: "Settings",
    moreTools: "More tools",
    moreToolsHelper: "Jump to deeper reports and tips.",
    moreAnalyticsHelper: "Track revenue, margin, and stock performance.",
    moreInsightsHelper: "See trends by day, week, and month.",
    moreExploreHelper: "Get quick tips for faster workflows.",
    slowMover: "Slow mover",
    stockHealthy: "Stock levels look healthy.",
    topRevenueItem: "Top revenue item",
    totalCost: "Total cost",
    totalRevenue: "Total revenue",
    totalSales: "Total sales",
    undo: "Undo",
    undoTransactionTitle: "Undo transaction?",
    undoTransactionBody:
      "This will reverse the transaction and remove it from history.",
    vendors: "Vendors",
    weekly: "Weekly",
    daily: "Daily",
    revenueVsRestock: "Revenue vs restock spend",
    currencyUSD: "US dollar (USD)",
    currencyVND: "Vietnamese dong (VND)",
    activeItems: "Active items",
    activate: "Activate",
    activeProducts: "Active products",
    addToCatalog: "Add to catalog",
    archive: "Archive",
    archiveProductBody:
      "This will hide {name} from your catalog without changing revenue or expenses.",
    archiveProductTitle: "Archive product?",
    catalogHelper:
      "Catalog items start with zero inventory and no expenses.",
    costPerUnit: "Cost per unit",
    deactivate: "Deactivate",
    edit: "Edit",
    inactiveProducts: "Inactive products",
    invalidCostBody: "Enter a valid cost.",
    invalidCostTitle: "Invalid cost",
    invalidInventoryBody: "Enter a valid inventory count.",
    invalidInventoryTitle: "Invalid inventory",
    invalidPriceBody: "Enter a valid price.",
    invalidPriceTitle: "Invalid price",
    inventoryHint:
      "Inventory changes do not affect revenue or expenses.",
    inventoryOnHand: "Inventory on hand",
    missingNameBody: "Enter a product name.",
    missingNameTitle: "Missing name",
    newProduct: "New product",
    noActiveProducts: "No active products.",
    noInactiveProducts: "No inactive products.",
    onHand: "on hand",
    pricePerUnit: "Price per unit",
    productName: "Product name",
    save: "Save",
    searchProducts: "Search products",
    searchPlaceholder: "Search by name",
    searchResultsEmpty: "No products match this search.",
    emptyInventoryTitle: "Add items before selling",
    emptyInventoryBody:
      "Create your catalog first so you can sell fast from the Inventory tab.",
    emptyInventoryCta: "Open catalog",
    updateProduct: "Update",
    vendorCatalogSubtitle:
      "Add or remove products without affecting revenue or expenses.",
    vendorCatalogTitle: "Vendor Catalog",
    left: "left",
  },
  vi: {
    analytics: "Phân tích",
    analyticsTitle: "Phân tích",
    appLanguage: "Ngôn ngữ ứng dụng",
    avgSale: "Giá trị trung bình",
    bestMarginItem: "Biên lợi nhuận cao nhất",
    bulkSale: "Bán số lượng lớn",
    bulkRestock: "Nhập hàng số lượng lớn",
    businessHealth: "Sức khỏe kinh doanh",
    cancel: "Hủy",
    changeLanguageHelper:
      "Đổi ngôn ngữ cho các nhãn trên toàn ứng dụng.",
    clear: "Xóa",
    clearHistory: "Xóa lịch sử",
    clearHistoryHelper:
      "Chọn khoảng thời gian để xóa lịch sử và cập nhật doanh thu, chi phí.",
    clearHistoryWarningTitle: "Xóa lịch sử?",
    clearHistoryWarningBody:
      "Thao tác này sẽ xóa các mục lịch sử tương ứng và cập nhật doanh thu, chi phí.",
    currency: "Tiền tệ",
    currencyHelper: "Chọn ký hiệu tiền tệ cho giá.",
    daysTracked: "Số ngày theo dõi",
    enterQuantity: "Nhập số lượng",
    enterValidQuantityTitle: "Nhập số lượng hợp lệ",
    enterValidQuantityBody: "Số lượng phải ít nhất là 1.",
    enterValidTotalTitle: "Nhập tổng chi phí hợp lệ",
    enterValidTotalBody: "Tổng chi phí phải lớn hơn hoặc bằng 0.",
    expenses: "Chi phí",
    estimatedTotal: "Tổng ước tính",
    explore: "Khám phá",
    exploreHeadline: "Mẹo nhanh cho ngày bán bận rộn.",
    exploreFastSalesTitle: "Bán nhanh từ tab Tồn kho",
    exploreFastSalesBody:
      "Nhấn − hoặc + để ghi nhận bán hàng và nhập hàng trong vài giây. Mỗi lần nhấn sẽ cập nhật tồn kho và doanh thu.",
    exploreBulkSalesTitle: "Nhấn giữ − để bán số lượng lớn",
    exploreBulkSalesBody:
      "Bán nhiều cùng lúc? Nhấn giữ − để nhập số lượng và tổng doanh thu, kể cả khi giảm giá.",
    exploreBulkRestockTitle: "Nhấn giữ + để nhập số lượng lớn",
    exploreBulkRestockBody:
      "Khi nhập nhiều cùng lúc, hãy nhấn giữ + để nhập số lượng và tổng chi phí trong một bước.",
    exploreCatalogTitle: "Giữ danh mục luôn cập nhật",
    exploreCatalogBody:
      "Tìm sản phẩm, cập nhật giá bán và giá vốn, chỉnh tồn kho, hoặc lưu trữ sản phẩm mà vẫn giữ lịch sử.",
    exploreUndoTitle: "Hoàn tác thao tác vừa rồi",
    exploreUndoBody:
      "Lỡ tay? Nhấn Hoàn tác để đảo ngược lần bán hoặc nhập hàng gần nhất.",
    exploreInsightsTitle: "Theo dõi xu hướng với Thông tin",
    exploreInsightsBody:
      "Xem doanh thu và chi phí nhập, xu hướng bán hàng, cùng hiệu suất sản phẩm theo khoảng báo cáo.",
    exploreHistoryTitle: "Theo dõi mọi giao dịch",
    exploreHistoryBody:
      "Lịch sử lưu lại bán hàng, nhập hàng và điều chỉnh để bạn xem nhanh các thời điểm bận rộn.",
    exploreAnalyticsTitle: "Biết sản phẩm bán chạy",
    exploreAnalyticsBody:
      "Phân tích hiển thị sản phẩm bán chạy, doanh thu và cảnh báo sắp hết hàng.",
    exploreSettingsTitle: "Cá nhân hóa cài đặt",
    exploreSettingsBody:
      "Đổi ngôn ngữ, chọn tiền tệ và xóa lịch sử khi cần bắt đầu lại.",
    grossMargin: "Biên lợi nhuận gộp",
    grossProfit: "Lợi nhuận gộp",
    history: "Lịch sử",
    historyTitle: "Lịch sử",
    historyEmpty:
      "Chưa có hoạt động. Bán hàng và nhập hàng sẽ hiển thị ở đây.",
    historySale: "Đã bán {quantity} {product} · {amount}",
    historyRestock: "Đã nhập {quantity} {product} · {amount}",
    historyAdjustment: "Điều chỉnh {quantity} {product} · {amount}",
    holdRestock:
      "Giữ + để nhập hàng số lượng lớn. Giữ − để bán số lượng lớn.",
    hourly: "Theo giờ",
    insufficientStockTitle: "Không đủ tồn kho",
    insufficientStockBody:
      "Bạn không thể bán nhiều hơn số lượng hiện có.",
    inventory: "Tồn kho",
    inventoryValue: "Giá trị tồn kho",
    inventoryWatch: "Theo dõi tồn kho",
    insights: "Thông tin",
    insightsTitle: "Thông tin",
    lifetimeRevenue: "Doanh thu tổng",
    language: "Ngôn ngữ",
    lowStock: "Sắp hết hàng",
    monthly: "Theo tháng",
    yearly: "Theo năm",
    allTime: "Mọi thời gian",
    mostRestockedItem: "Mặt hàng nhập nhiều nhất",
    mostSoldItem: "Mặt hàng bán chạy nhất",
    apply: "Áp dụng",
    periodMonth: "Tháng này",
    periodToday: "Hôm nay",
    periodWeek: "Tuần này",
    periodYear: "Năm nay",
    potentialRevenue: "Doanh thu tiềm năng",
    noRestocks: "Chưa có nhập hàng",
    noSales: "Chưa có bán hàng",
    quantity: "Số lượng",
    restock: "Nhập hàng",
    restockSpend: "Chi phí nhập hàng",
    reportRange: "Khoảng báo cáo",
    sales: "Bán hàng",
    salesTrend: "Xu hướng bán hàng",
    salesLogged: "giao dịch bán hàng đã ghi.",
    profit: "Lợi nhuận",
    productBreakdown: "Tổng quan sản phẩm",
    totalProducts: "Tổng số sản phẩm",
    productInsights: "Thông tin sản phẩm",
    qtyUnitCost: "số lượng × giá vốn",
    qtyUnitPrice: "số lượng × giá bán",
    revenue: "Doanh thu",
    restocked: "đã nhập",
    sold: "đã bán",
    salesOverview: "Tổng quan bán hàng",
    settings: "Cài đặt",
    settingsTitle: "Cài đặt",
    moreTools: "Công cụ bổ sung",
    moreToolsHelper: "Truy cập báo cáo chi tiết và mẹo nhanh.",
    moreAnalyticsHelper:
      "Theo dõi doanh thu, lợi nhuận và tồn kho.",
    moreInsightsHelper:
      "Xem xu hướng theo ngày, tuần và tháng.",
    moreExploreHelper: "Nhận mẹo để thao tác nhanh hơn.",
    slowMover: "Bán chậm",
    stockHealthy: "Tồn kho đang ổn định.",
    topRevenueItem: "Sản phẩm doanh thu cao nhất",
    totalCost: "Tổng chi phí",
    totalRevenue: "Tổng doanh thu",
    totalSales: "Tổng số bán",
    undo: "Hoàn tác",
    undoTransactionTitle: "Hoàn tác giao dịch?",
    undoTransactionBody:
      "Thao tác này sẽ đảo ngược giao dịch và xóa khỏi lịch sử.",
    vendors: "Nhà cung cấp",
    weekly: "Theo tuần",
    daily: "Theo ngày",
    revenueVsRestock: "Doanh thu và chi phí nhập",
    currencyUSD: "Đô la Mỹ (USD)",
    currencyVND: "Việt Nam đồng (VND)",
    activeItems: "Mặt hàng đang bán",
    activate: "Kích hoạt",
    activeProducts: "Sản phẩm đang hoạt động",
    addToCatalog: "Thêm vào danh mục",
    archive: "Lưu trữ",
    archiveProductBody:
      "Thao tác này sẽ ẩn {name} khỏi danh mục mà không thay đổi doanh thu hoặc chi phí.",
    archiveProductTitle: "Lưu trữ sản phẩm?",
    catalogHelper:
      "Danh mục bắt đầu với tồn kho bằng 0 và không có chi phí.",
    costPerUnit: "Giá vốn mỗi đơn vị",
    deactivate: "Tạm dừng",
    edit: "Chỉnh sửa",
    inactiveProducts: "Sản phẩm không hoạt động",
    invalidCostBody: "Nhập giá vốn hợp lệ.",
    invalidCostTitle: "Giá vốn không hợp lệ",
    invalidInventoryBody: "Nhập số lượng tồn kho hợp lệ.",
    invalidInventoryTitle: "Tồn kho không hợp lệ",
    invalidPriceBody: "Nhập giá hợp lệ.",
    invalidPriceTitle: "Giá không hợp lệ",
    inventoryHint:
      "Thay đổi tồn kho không ảnh hưởng đến doanh thu hoặc chi phí.",
    inventoryOnHand: "Tồn kho hiện tại",
    missingNameBody: "Nhập tên sản phẩm.",
    missingNameTitle: "Thiếu tên",
    newProduct: "Sản phẩm mới",
    noActiveProducts: "Không có sản phẩm hoạt động.",
    noInactiveProducts: "Không có sản phẩm không hoạt động.",
    onHand: "tồn kho",
    pricePerUnit: "Giá bán mỗi đơn vị",
    productName: "Tên sản phẩm",
    save: "Lưu",
    searchProducts: "Tìm sản phẩm",
    searchPlaceholder: "Tìm theo tên",
    searchResultsEmpty: "Không có sản phẩm phù hợp.",
    emptyInventoryTitle: "Thêm sản phẩm trước khi bán",
    emptyInventoryBody:
      "Tạo danh mục trước để bạn bán nhanh trong tab Tồn kho.",
    emptyInventoryCta: "Mở danh mục",
    updateProduct: "Cập nhật",
    vendorCatalogSubtitle:
      "Thêm hoặc xóa sản phẩm mà không ảnh hưởng doanh thu hoặc chi phí.",
    vendorCatalogTitle: "Danh mục nhà cung cấp",
    left: "còn lại",
  },
}

export const useLanguage = () => {
  const [language, setLanguageState] = useState<Language>(getLanguage())

  useEffect(() => {
    const unsubscribe = subscribeToLanguage(next => {
      setLanguageState(next)
    })
    return unsubscribe
  }, [])

  const t = useCallback(
    (key: TranslationKey) =>
      translations[language][key] ??
      translations.en[key] ??
      key,
    [language]
  )

  const updateLanguage = useCallback(
    (next: Language) => {
      setLanguage(next)
    },
    []
  )

  return useMemo(
    () => ({ language, setLanguage: updateLanguage, t }),
    [language, t, updateLanguage]
  )
}
