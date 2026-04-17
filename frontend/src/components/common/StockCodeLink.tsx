/** StockCodeLink — 股票代码高亮可点击，预留跳转模块二路由 */

import React from "react";
import { useNavigate } from "react-router-dom";

interface StockCodeLinkProps {
  code: string;
  name: string;
  style?: React.CSSProperties;
}

const StockCodeLink: React.FC<StockCodeLinkProps> = ({ code, name, style }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    // 预留模块二跳转路由 /market/stock/:code
    navigate(`/market/stock/${code}`);
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
      title={`${name} (${code}) — 查看详情`}
    >
      {name}({code})
    </span>
  );
};

export default StockCodeLink;
