import "./home.css";
import Banner from "./assets/banner.png";
import p1 from "./assets/hoodie.png";
import { ShoppingCart, User } from "lucide-react"; // Icons for Cart and Profile

const HomePage = () => {
  return (
    <div>
      {/* Navigation Bar */}
      <nav className="nav-bar">
        <div id="logo">
          <img src="" alt="logo" />
        </div>
        <div id="nav-bar-menu-left">
          <button>New & Featured</button>
          <button>Men</button>
          <button>Women</button>
          <button>Kids</button>
        </div>
        <div id="nav-bar-menu-right">
          <button aria-label="Cart">
            <ShoppingCart />
          </button>
          <button aria-label="Profile">
            <User />
          </button>
        </div>
      </nav>

      {/* Banner Section */}
      <section className="banner-new-featured">
        <img src={Banner} alt="New & Featured Banner" />
      </section>

      {/* Product Slides */}
      <ProductSection title="New & Featured" products={[p1, p1, p1]} />
      <ProductSection title="Limited Collections" products={[p1, p1, p1]} />
      <ProductSection title="Trending" products={[p1, p1, p1]} />
    </div>
  );
};

const ProductSection = ({ title, products }) => (
  <section className="product-slide">
    <div className="title">
      <h1>{title}</h1>
      <button>Explore more</button>
    </div>
    <div className="product-grid">
      {products.map((product, index) => (
        <ProductBox key={index} image={product} />
      ))}
    </div>
  </section>
);

const ProductBox = ({ image }) => (
  <div className="product-box">
    <img src={image} alt="Product" />
    <div className="product-box-info">
      <p>DIOR AND HYLTON NEL Hooded Sweatshirt</p>
      <p>AU$ 2,500.00</p>
    </div>
  </div>
);

export default HomePage;
