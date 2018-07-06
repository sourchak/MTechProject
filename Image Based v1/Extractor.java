import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import java.io.IOException;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.FileWriter;
import java.io.FileNotFoundException;

public class Extractor
{
    public static void main(String[] args)throws IOException, FileNotFoundException
    {
        System.out.print("Provide path the steganogram to be decrypted:");
        BufferedImage img= ImageIO.read(new File(new BufferedReader(new InputStreamReader(System.in)).readLine()));
        String message=extract(img);
        System.out.println("Secret message:\n"+message);
    }
    static String extract(BufferedImage steganogram)throws FileNotFoundException, IOException
    {
        FileWriter mFile=new FileWriter("./message.txt");
        String message="";
        char c=0;
        int x_lim=steganogram.getWidth();
        int y_lim=steganogram.getHeight();
        for(int x=0;x < x_lim && c!=31; x++)
            for (int y=0;y<y_lim && c != 31;y++)
            {
                long pixel=(long)steganogram.getRGB(x,y) & 0xffffffffL;
                int red=(int) (pixel>>16 & 0xff);
                int green=(int)(pixel>>8 & 0xff);
                int blue=(int)(pixel & 0xff);
                //System.out.println(red+" "+green+" "+blue);
                //System.out.println("bits:"+((red & 3))+" "+(green & 1)+" "+(blue & 3));
                int tmp=red & 3;
                tmp=(tmp<<1)+(green & 1);
                tmp=(tmp<<2)+(blue & 3);
                //System.out.println("tmp"+tmp+"\n");
                tmp=tmp & 31;
                if(tmp==31)
                {
                    c=31;
                    continue;
                }
                else
                    switch(tmp)
                    {
                        case 0:
                            c=' ';
                            break;
                        case 27:
                            c='.';
                            break;
                        case 28:
                            c=',';
                            break;
                        case 29:
                            c='?';
                            break;
                        case 30:
                            c='!';
                            break;
                        default :
                            c=(char)(tmp+65-1);
                    }
                mFile.write(c);
                message=message+String.valueOf(c);
            }
        mFile.close();
        return message.substring(0,message.length());
    }
}
