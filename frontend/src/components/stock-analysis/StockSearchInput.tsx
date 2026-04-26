/** StockSearchInput -- 股票搜索输入框（带防抖 + 候选列表） */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { AutoComplete, Typography, Tag } from "antd";
import { SearchOutlined, StockOutlined, CloseCircleOutlined } from "@ant-design/icons";
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
  const { setStock, setValidation, validationLoading, stockCode, stockName } =
    useStockAnalysisStore();

  const [keyword, setKeyword] = useState("");
  const [options, setOptions] = useState<{ value: string; label: React.ReactNode }[]>([]);
  const [selected, setSelected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const debouncedKeyword = useDebounce(keyword, 300);

  // 防抖后发起搜索请求
  useEffect(() => {
    if (!debouncedKeyword.trim() || selected) {
      return;
    }

    const doSearch = async () => {
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

        if (!result.valid) {
          setOptions([]);
          setValidation(false, false);
          setStock("", "");
          setSelected(false);
          return;
        }

        // 多个候选：展示下拉列表
        if (result.multiple && result.candidates && result.candidates.length > 0) {
          setOptions(
            result.candidates.map((c) => ({
              value: `${c.code}|${c.name}`,
              label: (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>
                    <Text style={{ fontSize: 13, color: "#061b31", marginRight: 8 }}>{c.name}</Text>
                    <Text style={{ fontSize: 12, color: "#94a3b8" }}>{c.code}</Text>
                  </span>
                  <Tag
                    style={{
                      fontSize: 10,
                      borderRadius: 3,
                      margin: 0,
                      background: c.market === "sh" ? "#f0fdf4" : "#eff6ff",
                      color: c.market === "sh" ? "#15be53" : "#3b82f6",
                      border: "none",
                    }}
                  >
                    {c.market === "sh" ? "沪" : "深"}
                  </Tag>
                </div>
              ),
            }))
          );
          setValidation(false, false);
          setStock("", "");
          return;
        }

        // 唯一匹配：直接选中
        if (result.stock_code && result.stock_name) {
          setStock(result.stock_code, result.stock_name);
          setKeyword(result.stock_name);
          setSelected(true);
          setOptions([]);
          setValidation(false, true);
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

    doSearch();

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
      setValidation(false, true);
    },
    [setStock, setValidation]
  );

  const handleSearch = (val: string) => {
    setKeyword(val);
    setSelected(false);
    if (!val.trim()) {
      setOptions([]);
      setStock("", "");
    }
  };

  const handleClear = useCallback(() => {
    setKeyword("");
    setSelected(false);
    setOptions([]);
    setStock("", "");
    setValidation(false, false);
  }, [setStock, setValidation]);

  return (
    <div style={{ width: "100%" }}>
      <AutoComplete
        value={keyword}
        options={options}
        onSearch={handleSearch}
        onSelect={handleSelect}
        style={{ width: "100%" }}
        placeholder="输入股票代码或名称，如 600519 或 贵州茅台"
        suffixIcon={validationLoading ? undefined : <SearchOutlined style={{ color: "#94a3b8" }} />}
        notFoundContent={
          keyword.trim() && !validationLoading && !selected ? (
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
          <CloseCircleOutlined
            style={{ fontSize: 14, color: "#94a3b8", cursor: "pointer" }}
            onClick={handleClear}
          />
        </div>
      )}
    </div>
  );
};

export default StockSearchInput;
