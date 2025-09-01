import React, { useState, useEffect } from "react";
import "./App.css"; // Import CSS for animations

const GRID_SIZE = 5; // 5x5 grid

const HeroGame = () => {
  const [position, setPosition] = useState({ x: 2, y: 2 }); // Start in the center

  const moveHero = (dx, dy) => {
    setPosition((prev) => {
      let newX = Math.max(0, Math.min(GRID_SIZE - 1, prev.x + dx));
      let newY = Math.max(0, Math.min(GRID_SIZE - 1, prev.y + dy));
      return { x: newX, y: newY };
    });
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      switch (event.key) {
        case "ArrowUp":
        case "w":
          moveHero(0, -1);
          break;
        case "ArrowDown":
        case "s":
          moveHero(0, 1);
          break;
        case "ArrowLeft":
        case "a":
          moveHero(-1, 0);
          break;
        case "ArrowRight":
        case "d":
          moveHero(1, 0);
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="game-container">
      <h1>Hero Movement Game</h1>
      <div className="grid">
        {Array.from({ length: GRID_SIZE }).map((_, row) =>
          Array.from({ length: GRID_SIZE }).map((_, col) => (
            <div key={`${row}-${col}`} className="cell">
              {position.x === col && position.y === row && (
                <div className="hero">🦸</div>
              )}
            </div>
          ))
        )}
      </div>
      <p>Use Arrow Keys or W A S D to move the hero.</p>
    </div>
  );
};

export default HeroGame;
