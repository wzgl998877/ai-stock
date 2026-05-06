/** StockCodeLink — 股票代码高亮可点击，打开侧边 Drawer 查看行情 */

import React from "react";
import { useStockDrawerStore } from "../../store/stockDrawerStore";

interface StockCodeLinkProps {
  code: string;
  name: string;
  style?: React.CSSProperties;
}

const StockCodeLink: React.FC<StockCodeLinkProps> = ({ code, name, style }) => {
  const openDrawer = useStockDrawerStore((s) => s.open);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    openDrawer(code);
  };

  return (
    <span
      onClick={handleClick}
      style={{
        color: "#533afd",
        cursor: "pointer",
        fontWeight: 400,
        fontSize: 12,
        fontFeatureSettings: "'ss01' on",
        borderBottom: "1px dashed #b9b9f9",
        ...style,
      }}
      title={`${name} (${code}) — 查看行情`}
    >
      {name}({code})
    </span>
  );
};

export default StockCodeLink;
