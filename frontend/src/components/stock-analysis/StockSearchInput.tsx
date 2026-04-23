/** StockSearchInput -- 股票搜索输入框（带防抖验证） */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { AutoComplete, Typography, Tag } from "antd";
import { SearchOutlined, StockOutlined } from "@ant-design/icons";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import * as stockAnalysisService from "../../services/stockAnalysisService";
import type { StockValidationResult } from "../../domain/types";

const { Text } = Typography;

/** 简易防抖 hook */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

const StockSearchInput: React.FC = () => {
  const { setStock, setValidation, validationLoading, validationValid, stockCode, stockName } =
    useStockAnalysisStore();

  const [keyword, setKeyword] = useState("");
  const [options, setOptions] = useState<{ value: string; label: React.ReactNode }[]>([]);
  const [selected, setSelected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const debouncedKeyword = useDebounce(keyword, 300);

  // 防抖后发起验证请求
  useEffect(() => {
    if (!debouncedKeyword.trim() || selected) {
      return;
    }

    const doValidate = async () => {
      // 取消上一次请求
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      setValidation(true, false);
      try {
        const result: StockValidationResult = await stockAnalysisService.validateStock(
          debouncedKeyword.trim()
        );
        if (controller.signal.aborted) return;

        if (result.valid) {
          // 与「从下拉选中」一致：验证通过即写入 store，避免仅 validationValid 为 true
          // 而 stockCode/stockName 仍为空，导致「开始分析」可点却不发请求。
          setStock(result.stock_code, result.stock_name);
          setKeyword(result.stock_name);
          setSelected(true);
          setOptions([]);
          setValidation(false, true);
        } else {
          setOptions([]);
          setValidation(false, false);
          setStock("", "");
          setSelected(false);
        }
      } catch {
        if (!controller.signal.aborted) {
          setOptions([]);
          setValidation(false, false);
          setStock("", "");
          setSelected(false);
        }
      }
    };

    doValidate();

    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [debouncedKeyword, selected, setValidation, setStock]);

  const handleSelect = useCallback(
    (val: string) => {
      const [code, name] = val.split("|");
      setStock(code, name);
      setKeyword(name);
      setSelected(true);
      setOptions([]);
    },
    [setStock]
  );

  const handleSearch = (val: string) => {
    setKeyword(val);
    setSelected(false);
    if (!val.trim()) {
      setOptions([]);
      setStock("", "");
    }
  };

  return (
    <div style={{ width: 480 }}>
      <AutoComplete
        value={keyword}
        options={options}
        onSearch={handleSearch}
        onSelect={handleSelect}
        style={{ width: "100%" }}
        placeholder="输入股票代码或名称，如 600519 或 贵州茅台"
        suffixIcon={validationLoading ? undefined : <SearchOutlined style={{ color: "#94a3b8" }} />}
        notFoundContent={
          keyword.trim() && !validationLoading && !validationValid && !selected ? (
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>未找到匹配的股票</Text>
          ) : null
        }
      />
      {selected && stockCode && (
        <div
          style={{
            marginTop: 8,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <Tag
            icon={<StockOutlined />}
            color="purple"
            style={{
              fontSize: 13,
              padding: "2px 8px",
              borderRadius: 4,
              background: "#f0efff",
              color: "#533afd",
              border: "1px solid #d6d9fc",
            }}
          >
            {stockName} ({stockCode})
          </Tag>
          <Text
            style={{
              fontSize: 12,
              color: "#15be53",
              fontFeatureSettings: "'ss01' on",
            }}
          >
            已选择
          </Text>
        </div>
      )}
    </div>
  );
};

export default StockSearchInput;
