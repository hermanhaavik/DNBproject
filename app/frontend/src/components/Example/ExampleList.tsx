import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is house insurance, and what does it cover?",
        value: "What is house insurance, and what does it cover?"
    },
    {
        text: "What is the difference between comprehensive and fully comprehensive car insurance?",
        value: "What is the difference between comprehensive and fully comprehensive car insurance?"
    },
    {   text: "How can I lower the price of my contents insurance?", 
        value: "How can I lower the price of my contents insurance?" 
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
