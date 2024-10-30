"
import React, { useState } from 'react';

interface ButtonProps {
  label: string;
  onClick?: () => void;
}

export const Button: React.FC<ButtonProps> = ({ label, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <button
      className={'bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded'}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {label}
    </button>
  );
};
"
