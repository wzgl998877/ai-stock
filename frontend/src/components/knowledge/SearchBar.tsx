/** SearchBar — 搜索输入框 + 防抖 + 关键词高亮 */

import React, { useState, useEffect, useRef } from "react";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const SearchBar: React.FC<Props> = ({ value, onChange, placeholder = "搜索知识库..." }) => {
  const [localValue, setLocalValue] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (val: string) => {
    setLocalValue(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onChange(val);
    }, 500);
  };

  return (
    <Input
      prefix={<SearchOutlined style={{ color: "#b0b8c4" }} />}
      value={localValue}
      onChange={(e) => handleChange(e.target.value)}
      placeholder={placeholder}
      allowClear
      variant="outlined"
      className="search-input"
      style={{
        borderRadius: 6,
        maxWidth: 400,
        fontFeatureSettings: "'ss01' on",
      }}
    />
  );
};

export default SearchBar;
